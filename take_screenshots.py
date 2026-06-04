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
        
        try:
            await page.wait_for_selector("text=Recommender Scoring", timeout=15000)
            await page.wait_for_timeout(3000) # Wait for Plotly charts to finish rendering
            print("Taking results screenshot...")
            await page.screenshot(path="dashboard_results.png", full_page=True)
            
            # Scroll to 3D Geometric Analysis and screenshot it
            print("Taking 3D Geometry screenshot...")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await page.wait_for_timeout(2000)
            await page.screenshot(path="dashboard_3d_geometry.png")
            
            # Click "Compute 3D Volume" and take screenshot of the volume rendering
            print("Computing 3D Volume...")
            await page.locator("button", has_text="Compute 3D Volume").click()
            await page.wait_for_timeout(5000) # Wait for PDE solver and Plotly 3D rendering
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
            print("Taking 3D Volume screenshot...")
            await page.screenshot(path="dashboard_3d_volume.png")
            
        except Exception as e:
            print("Failed to wait for results:", e)
            await page.screenshot(path="dashboard_results_error.png", full_page=True)
            
        await browser.close()
        print("Screenshots saved: dashboard_main.png, dashboard_results.png, dashboard_3d_geometry.png, dashboard_3d_volume.png")

if __name__ == "__main__":
    asyncio.run(main())
