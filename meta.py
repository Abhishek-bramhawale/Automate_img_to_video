from playwright.sync_api import sync_playwright 
import os
import time
import psutil
import shutil

download_folder = os.path.abspath("downloads")
images_folder = os.path.abspath("images")
processed_folder = os.path.abspath("processed")

os.makedirs(download_folder, exist_ok=True)
os.makedirs(images_folder, exist_ok=True)
os.makedirs(processed_folder, exist_ok=True)

brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
user_data_dir = r"C:\Users\sanji\AppData\Local\BraveSoftware\Brave-Browser\User Data"

print("Checking if Brave is already running...")
for proc in psutil.process_iter(['name']):
    if proc.info['name'] and 'brave' in proc.info['name'].lower():
        print("WARNING: Brave is already running! Close all Brave windows first.")

with sync_playwright() as p:
    # def handle_download(download):
    #     download_path = os.path.join(download_folder, download.suggested_filename)
    #     print(f"Download starting: {download.suggested_filename}")
    #     download.save_as(download_path)
    #     print(f"Download completed: {download_path}")

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

    # browser.on("download", handle_download)   # commented out

    page = browser.pages[0] if browser.pages else browser.new_page()
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    image_files = [os.path.join(images_folder, f) for f in os.listdir(images_folder)
                   if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]

    if not image_files:
        print("No images found in 'images' folder!")
        browser.close()
        exit(1)

    print(f"Found {len(image_files)} images to process:")
    for i, img in enumerate(image_files, 1):
        print(f"  {i}. {os.path.basename(img)}")

    # === LOOP START ===
    for index, image_path in enumerate(image_files, 1):
        image_name = os.path.basename(image_path)
        print(f"\n{'='*60}")
        print(f"PROCESSING IMAGE {index}/{len(image_files)}: {image_name}")
        print(f"{'='*60}")

        try:
            page.goto("/", timeout=90000) #use meta site here
            time.sleep(5)

            if not os.path.exists(image_path):
                print(f"Image '{image_path}' not found!")
                continue

            # Upload image
            upload_input = page.query_selector("input[type='file']")
            if upload_input:
                upload_input.set_input_files(image_path)
                print("Uploading image... please wait...")
                page.wait_for_selector("//span[text()='Animate']/ancestor::div[@role='button']", timeout=120000)
                print("Image upload complete")
            else:
                print("Upload input not found")
                continue

            # Click Animate
            print("Waiting for 'Animate' button...")
            animate_btn = page.wait_for_selector("//span[text()='Animate']/ancestor::div[@role='button']", timeout=60000)
            if animate_btn:
                time.sleep(6)
                animate_btn.click()
                print("Clicked 'Animate'")
            else:
                print("Animate button not found")
                continue

            # Wait for generation
            print("Waiting for processing to finish (download btn indicator)...")
            download_btn = page.wait_for_selector("div[aria-label='Download media']", timeout=300000)

            if download_btn:
                print("Animation finished (download button appeared)")
            else:
                print("Download button not detected, skipping download")
                continue

            # Move processed image
            try:
                dest = os.path.join(processed_folder, image_name)
                shutil.move(image_path, dest)
                print(f"Moved processed image to: {dest}")
            except Exception as move_err:
                print(f"Could not move image: {move_err}")

            # Refresh for next round
            print("Refreshing for next image...")
            page.reload()
            time.sleep(5)

        except Exception as e:
            print(f"Error processing {image_name}: {e}")
            continue
    # === LOOP END ===

    print("\nAll images processed successfully!")
    browser.close()
