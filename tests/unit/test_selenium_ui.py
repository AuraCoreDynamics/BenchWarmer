"""Selenium WebDriver end-to-end unit tests and UI screenshot capture for BenchWarmer."""

from pathlib import Path
import threading
import time
import unittest

from benchwarmer.api import BenchWarmer
from benchwarmer.web.server import create_fastapi_app, find_available_port

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SCREENSHOTS_DIR = ROOT_DIR / "docs" / "screenshots"


class TestSeleniumUI(unittest.TestCase):
    driver = None
    server = None
    port = None
    server_thread = None

    @classmethod
    def setUpClass(cls):
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

        # Check for selenium
        try:
            from selenium import webdriver
            from selenium.webdriver.edge.options import Options as EdgeOptions
            from selenium.webdriver.chrome.options import Options as ChromeOptions
        except ImportError:
            raise unittest.SkipTest("Selenium is not installed in the current environment.")

        # Try Edge first, fallback to Chrome
        driver = None
        for browser_cls, opts_cls in [
            (webdriver.Edge, EdgeOptions),
            (webdriver.Chrome, ChromeOptions),
        ]:
            try:
                opts = opts_cls()
                opts.add_argument("--headless=new")
                opts.add_argument("--no-sandbox")
                opts.add_argument("--disable-gpu")
                opts.add_argument("--window-size=1600,1050")
                driver = browser_cls(options=opts)
                break
            except Exception:
                continue

        if driver is None:
            raise unittest.SkipTest("Neither Edge nor Chrome headless webdriver could be initialized.")

        cls.driver = driver

        # Start Web Server in background thread
        try:
            import uvicorn
            has_uvicorn = True
        except ImportError:
            has_uvicorn = False

        cls.port = find_available_port("127.0.0.1", 8930)
        bw = BenchWarmer()
        app = create_fastapi_app(bw=bw)

        if has_uvicorn:
            config = uvicorn.Config(app, host="127.0.0.1", port=cls.port, log_level="critical")
            cls.server = uvicorn.Server(config)
            cls.server_thread = threading.Thread(target=cls.server.run, daemon=True)
            cls.server_thread.start()
        else:
            raise unittest.SkipTest("Uvicorn required for Selenium headless server tests.")

        time.sleep(1.5)

    @classmethod
    def tearDownClass(cls):
        if cls.driver:
            try:
                cls.driver.quit()
            except Exception:
                pass

        if cls.server:
            cls.server.should_exit = True

    def setUp(self):
        self.url = f"http://127.0.0.1:{self.port}"
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        self.By = By
        self.WebDriverWait = WebDriverWait
        self.EC = EC

    def test_01_leaderboard_overview_render_and_screenshot(self):
        driver = self.driver
        driver.get(self.url)
        self.WebDriverWait(driver, 10).until(
            self.EC.presence_of_element_located((self.By.CSS_SELECTOR, "#table-body tr"))
        )
        self.assertIn("BenchWarmer", driver.title)

        badge = driver.find_element(self.By.ID, "badge-model-count").text
        self.assertIn("1,449", badge)

        rows = driver.find_elements(self.By.CSS_SELECTOR, "#table-body tr")
        self.assertEqual(len(rows), 50)

        # Allow layout & font rendering
        time.sleep(1.0)
        shot_path = SCREENSHOTS_DIR / "01_leaderboard_overview.png"
        driver.save_screenshot(str(shot_path))
        self.assertTrue(shot_path.exists())
        self.assertGreater(shot_path.stat().st_size, 10000)

    def test_02_provider_and_license_filtering_and_screenshot(self):
        from selenium.webdriver.support.ui import Select

        driver = self.driver
        # Select Provider 'openai'
        org_sel = Select(driver.find_element(self.By.ID, "org-filter-select"))
        org_sel.select_by_value("openai")
        time.sleep(0.4)

        # Select License 'apache-2.0'
        lic_sel = Select(driver.find_element(self.By.ID, "license-filter-select"))
        lic_sel.select_by_value("apache-2.0")
        time.sleep(0.4)

        # Active filter chips visible
        chips_container = driver.find_element(self.By.ID, "active-filter-chips")
        self.assertTrue(chips_container.is_displayed())

        org_chip = driver.find_element(self.By.ID, "active-org-chip")
        self.assertTrue(org_chip.is_displayed())
        self.assertIn("openai", driver.find_element(self.By.ID, "active-org-text").text.lower())

        lic_chip = driver.find_element(self.By.ID, "active-license-chip")
        self.assertTrue(lic_chip.is_displayed())
        self.assertIn("apache-2.0", driver.find_element(self.By.ID, "active-license-text").text.lower())

        # Table should only show openai apache-2.0 models (e.g. gpt-oss-120b, gpt-oss-20b)
        rows = driver.find_elements(self.By.CSS_SELECTOR, "#table-body tr")
        self.assertTrue(len(rows) >= 2)
        match_count = driver.find_element(self.By.ID, "match-count").text
        self.assertIn("models displayed", match_count)

        time.sleep(0.5)
        shot_path = SCREENSHOTS_DIR / "02_provider_and_license_filtering.png"
        driver.save_screenshot(str(shot_path))
        self.assertTrue(shot_path.exists())

        # Reset filters
        driver.find_element(self.By.ID, "btn-reset-filters").click()
        time.sleep(0.4)
        self.assertFalse(chips_container.is_displayed())
        reset_rows = driver.find_elements(self.By.CSS_SELECTOR, "#table-body tr")
        self.assertEqual(len(reset_rows), 50)

    def test_03_interactive_tag_click_and_context_menu_clear(self):
        from selenium.webdriver.common.action_chains import ActionChains

        driver = self.driver
        # Click on the first org tag in table
        first_org_tag = driver.find_element(self.By.CSS_SELECTOR, "#table-body tr .org-tag[data-org]")
        target_org = first_org_tag.get_attribute("data-org")

        first_org_tag.click()
        time.sleep(0.4)

        # Assert active chip matches target_org
        org_chip = driver.find_element(self.By.ID, "active-org-chip")
        self.assertTrue(org_chip.is_displayed())
        self.assertEqual(driver.find_element(self.By.ID, "active-org-text").text, target_org)

        # Right click on an org tag to clear filter
        tag_to_right_click = driver.find_element(self.By.CSS_SELECTOR, "#table-body tr .org-tag[data-org]")
        actions = ActionChains(driver)
        actions.context_click(tag_to_right_click).perform()
        time.sleep(0.4)

        # Assert org chip is now cleared
        self.assertFalse(org_chip.is_displayed())

    def test_04_model_scorecard_modal_and_screenshot(self):
        from selenium.webdriver.common.action_chains import ActionChains

        driver = self.driver
        # Double click the first row
        row = driver.find_element(self.By.CSS_SELECTOR, "#table-body tr")
        actions = ActionChains(driver)
        actions.double_click(row).perform()

        self.WebDriverWait(driver, 5).until(
            self.EC.visibility_of_element_located((self.By.ID, "modal-scorecard"))
        )
        time.sleep(0.6)

        # Assert scorecard elements
        sc_name = driver.find_element(self.By.ID, "sc-model-name").text
        self.assertTrue(len(sc_name) > 0)

        # Assert radar chart SVG rendered
        radar_svg = driver.find_element(self.By.CSS_SELECTOR, "#modal-scorecard .svg-chart")
        self.assertIsNotNone(radar_svg)

        # Assert metric cards
        cards = driver.find_elements(self.By.CSS_SELECTOR, "#sc-metric-cards .metric-card")
        self.assertEqual(len(cards), 7)

        # Assert VRAM footprint table rows
        vram_rows = driver.find_elements(self.By.CSS_SELECTOR, "#sc-vram-table tbody tr")
        self.assertTrue(len(vram_rows) >= 1)

        shot_path = SCREENSHOTS_DIR / "03_model_scorecard_radar.png"
        driver.save_screenshot(str(shot_path))
        self.assertTrue(shot_path.exists())

        # Close modal
        driver.find_element(self.By.CSS_SELECTOR, "#modal-scorecard .modal-close").click()
        time.sleep(0.4)

    def test_04b_scorecard_reopen_and_distinctive_evals_and_tooltips(self):
        from selenium.webdriver.common.action_chains import ActionChains

        driver = self.driver
        try:
            # 1. Assert benchmark column headers have full hover tooltips and descriptions
            th_hf = driver.find_element(self.By.CSS_SELECTOR, "th[data-sort='hf_v2_avg']")
            hf_title = th_hf.get_attribute("title")
            self.assertIn("Leaderboard", hf_title)
            self.assertIn("IFEval", hf_title)

            th_elo = driver.find_element(self.By.CSS_SELECTOR, "th[data-sort='arena_elo_raw']")
            self.assertIn("Chatbot Arena", th_elo.get_attribute("title"))

            # 2. Assert reopening scorecard after previous close (verifying radar SVG ID preservation fix)
            sc_buttons = driver.find_elements(self.By.CSS_SELECTOR, "#table-body tr .btn-icon-scorecard")
            self.assertGreater(len(sc_buttons), 1)
            sc_buttons[1].click()
            self.WebDriverWait(driver, 5).until(
                self.EC.visibility_of_element_located((self.By.ID, "modal-scorecard"))
            )
            time.sleep(0.4)
            reopened_name = driver.find_element(self.By.ID, "sc-model-name").text
            self.assertTrue(len(reopened_name) > 0)
            driver.find_element(self.By.CSS_SELECTOR, "#modal-scorecard .modal-close").click()
            time.sleep(0.4)

            # 3. Search for 'mythos' to verify filter + scorecard opening + distinctive evals
            search_input = driver.find_element(self.By.ID, "search-input")
            search_input.clear()
            search_input.send_keys("mythos")
            time.sleep(0.5)

            mythos_row = driver.find_element(self.By.CSS_SELECTOR, "#table-body tr")
            actions = ActionChains(driver)
            actions.double_click(mythos_row).perform()

            self.WebDriverWait(driver, 5).until(
                self.EC.visibility_of_element_located((self.By.ID, "modal-scorecard"))
            )
            time.sleep(0.6)

            sc_name = driver.find_element(self.By.ID, "sc-model-name").text
            self.assertIn("mythos", sc_name.lower())

            # Assert Distinctive Frontier Evals container is visible and has cards
            dist_container = driver.find_element(self.By.ID, "sc-distinctive-container")
            self.assertTrue(dist_container.is_displayed())

            dist_cards = driver.find_elements(self.By.CSS_SELECTOR, "#sc-distinctive-cards .metric-card")
            self.assertGreaterEqual(len(dist_cards), 4)

            # Verify SWE-bench and CyberGym are present in distinctive cards
            dist_text = dist_container.text.lower()
            self.assertIn("swe-bench verified", dist_text)
            self.assertIn("cybergym", dist_text)

            shot_path = SCREENSHOTS_DIR / "09_frontier_evals_scorecard.png"
            driver.save_screenshot(str(shot_path))
            self.assertTrue(shot_path.exists())
        finally:
            # Ensure modal is closed and search input is cleared even if assertions fail
            try:
                driver.execute_script("document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('open'));")
                driver.execute_script("document.getElementById('search-input').value = ''; document.getElementById('search-input').dispatchEvent(new Event('input'));")
                time.sleep(0.4)
            except Exception:
                pass

    def test_05_multi_model_comparison_and_screenshot(self):
        driver = self.driver
        # Select checkboxes for first 3 rows
        cbs = driver.find_elements(self.By.CSS_SELECTOR, "#table-body tr input.row-select-cb")
        self.assertGreaterEqual(len(cbs), 3)
        for cb in cbs[:3]:
            if not cb.is_selected():
                cb.click()
        time.sleep(0.3)

        cmp_btn = driver.find_element(self.By.ID, "btn-open-compare")
        self.assertTrue(cmp_btn.is_enabled())
        self.assertEqual(driver.find_element(self.By.ID, "compare-count").text, "3")

        cmp_btn.click()
        self.WebDriverWait(driver, 5).until(
            self.EC.visibility_of_element_located((self.By.ID, "modal-compare"))
        )
        time.sleep(0.6)

        # Assert model count badge in compare modal
        count_text = driver.find_element(self.By.ID, "cmp-model-count").text
        self.assertEqual(count_text, "3 Models")

        # Assert radar legend has 3 entries
        legend_items = driver.find_elements(self.By.CSS_SELECTOR, "#cmp-radar-legend > div")
        self.assertEqual(len(legend_items), 3)

        # Assert specs table
        specs_rows = driver.find_elements(self.By.CSS_SELECTOR, "#cmp-specs-body tr")
        self.assertTrue(len(specs_rows) >= 6)

        shot_path = SCREENSHOTS_DIR / "04_multi_model_comparison.png"
        driver.save_screenshot(str(shot_path))
        self.assertTrue(shot_path.exists())

        # Close compare modal
        driver.find_element(self.By.CSS_SELECTOR, "#modal-compare .modal-close").click()
        time.sleep(0.4)

    def test_06_pareto_frontier_and_screenshot(self):
        driver = self.driver
        driver.find_element(self.By.ID, "btn-open-pareto").click()
        self.WebDriverWait(driver, 5).until(
            self.EC.visibility_of_element_located((self.By.ID, "modal-pareto"))
        )
        time.sleep(0.6)

        # Check SVG scatter plot and table
        svg_dots = driver.find_elements(self.By.CSS_SELECTOR, "#pareto-svg circle.scatter-dot")
        self.assertGreater(len(svg_dots), 10)

        frontier_rows = driver.find_elements(self.By.CSS_SELECTOR, "#pareto-table-body tr")
        self.assertGreater(len(frontier_rows), 2)

        shot_path = SCREENSHOTS_DIR / "05_pareto_frontier_routing.png"
        driver.save_screenshot(str(shot_path))
        self.assertTrue(shot_path.exists())

        # Close Pareto modal
        driver.find_element(self.By.CSS_SELECTOR, "#modal-pareto .modal-close").click()
        time.sleep(0.4)

    def test_07_contamination_audit_and_screenshot(self):
        driver = self.driver
        driver.find_element(self.By.ID, "btn-open-audit").click()
        self.WebDriverWait(driver, 5).until(
            self.EC.visibility_of_element_located((self.By.ID, "modal-audit"))
        )
        time.sleep(0.6)

        # Check audit rows
        audit_rows = driver.find_elements(self.By.CSS_SELECTOR, "#audit-table-body tr")
        self.assertGreater(len(audit_rows), 50)

        # Check for HIGH_CONTAMINATION_RISK badge
        badges = driver.find_elements(self.By.CSS_SELECTOR, "#audit-table-body .badge-red")
        self.assertTrue(len(badges) > 0)

        shot_path = SCREENSHOTS_DIR / "06_contamination_audit.png"
        driver.save_screenshot(str(shot_path))
        self.assertTrue(shot_path.exists())

        # Close audit modal
        driver.find_element(self.By.CSS_SELECTOR, "#modal-audit .modal-close").click()
        time.sleep(0.4)

    def test_08_custom_weighted_scorer_and_screenshot(self):
        driver = self.driver
        # Switch to Custom Scorer view
        driver.find_element(self.By.CSS_SELECTOR, '.tab-btn[data-view="scorer"]').click()
        time.sleep(0.5)

        # Check slider panel is displayed
        scorer_panel = driver.find_element(self.By.ID, "scorer-panel")
        self.assertTrue(scorer_panel.is_displayed())

        # Check sliders
        sliders = driver.find_elements(self.By.CSS_SELECTOR, ".weight-slider")
        self.assertEqual(len(sliders), 7)

        # Click preset Math Specialist
        driver.find_element(self.By.ID, "preset-math").click()
        time.sleep(0.4)

        # Check Math Hard slider value is 3.0
        math_disp = driver.find_element(self.By.ID, "disp-wt-math_hard").text
        self.assertEqual(math_disp, "3.0")

        shot_path = SCREENSHOTS_DIR / "07_custom_weighted_scorer.png"
        driver.save_screenshot(str(shot_path))
        self.assertTrue(shot_path.exists())

    def test_09_advanced_benchmark_filters_and_screenshot(self):
        from selenium.webdriver.support.ui import Select

        driver = self.driver
        # Switch back to leaderboard
        driver.find_element(self.By.CSS_SELECTOR, '.tab-btn[data-view="leaderboard"]').click()
        time.sleep(0.4)

        # Open Benchmark Filters drawer
        btn_adv = driver.find_element(self.By.ID, "btn-toggle-adv-filter")
        btn_adv.click()
        time.sleep(0.4)

        adv_panel = driver.find_element(self.By.ID, "advanced-filters-panel")
        self.assertTrue(adv_panel.is_displayed())

        # Select a reference model
        beat_sel = Select(driver.find_element(self.By.ID, "beat-model-select"))
        if len(beat_sel.options) > 2:
            beat_sel.select_by_index(2)
        time.sleep(0.3)

        shot_path = SCREENSHOTS_DIR / "08_advanced_benchmark_filters.png"
        driver.save_screenshot(str(shot_path))
        self.assertTrue(shot_path.exists())


if __name__ == "__main__":
    unittest.main()
