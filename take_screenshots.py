import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 1000})
        
        print("Navigating to Streamlit app...")
        # Wait for Streamlit to load completely
        await page.goto("http://localhost:8501", wait_until="networkidle")
        await page.wait_for_timeout(3000) # Give it 3 extra seconds for initial render
        
        # Take initial dashboard screenshot
        print("Taking initial screenshot...")
        await page.screenshot(path="dashboard_main.png", full_page=False)
        
        # Click the 'Run Multi-Material Comparative Study' button
        print("Running simulation...")
        await page.locator("button", has_text="Run Multi-Material Comparative Study").click()
        
        # Wait for the results to load (wait for the Recommender Scoring subheader)
        try:
            await page.wait_for_selector("text=Recommender Scoring", timeout=15000)
            await page.wait_for_timeout(3000) # Wait for Plotly charts to finish rendering
            print("Taking results screenshot...")
            await page.screenshot(path="dashboard_results.png", full_page=True)
        except Exception as e:
            print("Failed to wait for results:", e)
            await page.screenshot(path="dashboard_results_error.png", full_page=True)
            
        await browser.close()
        print("Screenshots saved: dashboard_main.png, dashboard_results.png")

if __name__ == "__main__":
    asyncio.run(main())
