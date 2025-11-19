from playwright.sync_api import sync_playwright
import os
import time
import psutil
import shutil

prompt_text = "talking"
download_folder = os.path.abspath("downloads")
images_folder = os.path.abspath("images")
processed_folder = os.path.abspath("processed")

os.makedirs(download_folder, exist_ok=True)
os.makedirs(images_folder, exist_ok=True)
os.makedirs(processed_folder, exist_ok=True)

brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
user_data_dir = r"C:\Users\sanji\AppData\Local\BraveSoftware\Brave-Browser\User Data"

def check_and_bypass_turnstile(page, wait_time=25, check_timeout=40):
    """
    Detects and bypasses Cloudflare Turnstile if it appears
    
    Args:
        page: Playwright page object
        wait_time: How long to wait for turnstile to appear (default 25s)
        check_timeout: Total timeout for the entire bypass process (default 40s)
    
    Returns True if bypass successful or no turnstile found, False if timeout
    """
    print(f"🔍 Monitoring for Cloudflare Turnstile (will wait up to {wait_time}s for it to appear)...")
    start_time = time.time()
    turnstile_found = False
    
    # Phase 1: Wait and watch for turnstile to appear
    while time.time() - start_time < wait_time:
        try:
            # Check for Turnstile iframe
            turnstile_iframe = page.query_selector("iframe[src*='challenges.cloudflare.com'], iframe[src*='turnstile']")
            
            if turnstile_iframe:
                turnstile_found = True
                print("⚠️  Cloudflare Turnstile detected! Attempting bypass...")
                
                # Give iframe time to fully load
                time.sleep(2)
                
                # Switch to iframe context
                frame = turnstile_iframe.content_frame()
                
                if frame:
                    # Look for the checkbox/button to click
                    checkbox = frame.query_selector("input[type='checkbox']")
                    if checkbox:
                        print("✅ Found checkbox, clicking...")
                        checkbox.click()
                        time.sleep(2)
                    
                    # Alternative: look for clickable label/span
                    clickable = frame.query_selector("label, span[role='button'], div[role='button']")
                    if clickable and not checkbox:
                        print("✅ Found clickable element, clicking...")
                        clickable.click()
                        time.sleep(2)
                    
                    # Wait for verification to complete
                    print("⏳ Waiting for verification...")
                    
                    # Wait up to 15 seconds for turnstile to disappear
                    verification_start = time.time()
                    while time.time() - verification_start < 15:
                        if not page.query_selector("iframe[src*='challenges.cloudflare.com'], iframe[src*='turnstile']"):
                            print("✅ Turnstile bypassed successfully!")
                            return True
                        time.sleep(0.5)
                    
                    print("⚠️  Verification taking longer than expected, continuing anyway...")
                    return True
                else:
                    print("⚠️  Could not access iframe content, continuing...")
                    return True
                    
        except Exception as e:
            print(f"⚠️  Error during turnstile check: {e}")
        
        # Show progress every 5 seconds
        elapsed = int(time.time() - start_time)
        if elapsed % 5 == 0 and elapsed > 0:
            print(f"⏳ Still waiting for Turnstile... ({elapsed}s / {wait_time}s)")
        
        time.sleep(1)
    
    # Phase 2: No turnstile appeared within wait time
    if not turnstile_found:
        print("✅ No Turnstile detected after waiting, proceeding...")
        return True
    
    # Phase 3: Turnstile found but couldn't bypass
    if time.time() - start_time >= check_timeout:
        print("❌ Turnstile bypass timeout reached")
        return False
    
    return True

print("Checking if Brave is already running...")
for proc in psutil.process_iter(['name']):
    if proc.info['name'] and 'brave' in proc.info['name'].lower():
        print("⚠️  WARNING: Brave is already running! Close all Brave windows first.")

with sync_playwright() as p:
    def handle_download(download):
        download_path = os.path.join(download_folder, download.suggested_filename)
        print(f"Download starting: {download.suggested_filename}")
        download.save_as(download_path)
        print(f"✅ Download completed: {download_path}")

    browser = p.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        headless=False,
        executable_path=brave_path,
        accept_downloads=True,
        ignore_default_args=["--disable-extensions"],
        viewport=None,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-web-security",
            "--allow-running-insecure-content",
            "--disable-features=VizDisplayCompositor",
            f"--download-default-directory={download_folder}"
        ]
    )

    browser.on("download", handle_download)
    page = browser.pages[0] if browser.pages else browser.new_page()
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    image_files = []
    for file in os.listdir(images_folder):
        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
            image_files.append(os.path.join(images_folder, file))
    
    if not image_files:
        print("❌ No images found in 'images' folder!")
        browser.close()
        exit(1)
    
    print(f"Found {len(image_files)} images to process:")
    for i, img in enumerate(image_files, 1):
        print(f"  {i}. {os.path.basename(img)}")

    for index, image_path in enumerate(image_files, 1):
        image_name = os.path.basename(image_path)
        print(f"\n{'='*60}")
        print(f"PROCESSING IMAGE {index}/{len(image_files)}: {image_name}")
        print(f"{'='*60}")
        
        try:
            print("Opening site...")
            page.goto("https://www.yeschat.ai/features/image-to-video", timeout=90000)
            time.sleep(5)

            if not os.path.exists(image_path):
                print(f"❌ Image '{image_path}' not found!")
                continue

            upload_input = page.query_selector("input[type='file']")
            if upload_input:
                upload_input.set_input_files(image_path)
                print("✅ Image uploaded")
            else:
                print("❌ Upload input not found")
                continue

            time.sleep(15)

            prompt_box = page.query_selector("textarea, input[type='text']")
            if prompt_box:
                prompt_box.fill(prompt_text)
                print("✅ Prompt filled")
            else:
                print("❌ Prompt box not found")
                continue

            selected = False
            for btn in page.query_selector_all("button"):
                if btn.inner_text().strip() == "540P":
                    btn.click()
                    selected = True
                    print("✅ 540P selected")
                    break
            if not selected:
                print("❌ 540P button not found")
                continue

            time.sleep(1)
            generate_btn = page.query_selector("button:has-text('Generate'), button:has-text('Create')")
            if generate_btn:
                print("Clicking Generate...")
                generate_btn.click()
                
                # 🔥 CHECK FOR TURNSTILE AFTER CLICKING GENERATE
                # Wait up to 25 seconds for turnstile to appear, total timeout 40 seconds
                if not check_and_bypass_turnstile(page, wait_time=25, check_timeout=40):
                    print("❌ Failed to bypass Turnstile, skipping this image")
                    continue
            else:
                print("❌ Generate button not found")
                continue

            print("Waiting for processing to complete...")
            
            try:
                download_button = page.wait_for_selector(
                    'button.z-0.group.relative.inline-flex.items-center.justify-center.box-border.appearance-none.select-none.whitespace-nowrap.font-normal.subpixel-antialiased.overflow-hidden.tap-highlight-transparent', 
                    timeout=300000,
                    state='visible'
                )
                
                if download_button:
                    print("✅ Processing complete! Download button appeared.")
                    print("Clicking download button...")
                    
                    with page.expect_download() as download_info:
                        download_button.click()
                    
                    download = download_info.value
                    download_path = os.path.join(download_folder, download.suggested_filename)
                    download.save_as(download_path)
                    print(f"✅ Download completed: {download_path}")
                    
                else:
                    print("❌ Download button not found within timeout")
                    continue
                    
            except Exception as e:
                print(f"❌ Error waiting for/downloading: {e}")
                
                try:
                    completion_text = page.wait_for_selector(
                        "text=/complete|ready|finished|done/i", 
                        timeout=10000
                    )
                    if completion_text:
                        print("✅ Processing complete detected via text")
                        
                        download_button = page.query_selector(
                            'button[class*="z-0 group relative inline-flex"]'
                        )
                        if download_button:
                            print("Clicking download button...")
                            with page.expect_download() as download_info:
                                download_button.click()
                            
                            download = download_info.value
                            download_path = os.path.join(download_folder, download.suggested_filename)
                            download.save_as(download_path)
                            print(f"✅ Download completed: {download_path}")
                except Exception as fallback_error:
                    print(f"Fallback also failed: {fallback_error}")
                    continue

            # ✅ Move processed image to "processed" folder
            try:
                dest = os.path.join(processed_folder, image_name)
                shutil.move(image_path, dest)
                print(f"✅ Moved processed image to: {dest}")
            except Exception as move_err:
                print(f"❌ Could not move image: {move_err}")

            print(f"✅ Completed processing for {image_name}")
            time.sleep(3)

        except Exception as e:
            print(f"❌ Error processing {image_name}: {e}")
            continue

    print(f"\n{'='*60}")
    print("PROCESSING COMPLETE!")
    print(f"{'='*60}")
    
    downloaded_files = os.listdir(download_folder)
    if downloaded_files:
        print("Files in download folder:")
        for file in downloaded_files:
            file_path = os.path.join(download_folder, file)
            print(f"  - {file} (size: {os.path.getsize(file_path)} bytes)")
    else:
        print("❌ No files found in download folder")

    print("\nClosing browser...")
    browser.close()
    print("✅ Browser closed. All images processed!")