from playwright.sync_api import sync_playwright
import os
import time
import psutil
import winsound
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

print("Checking if Brave is already running...")
for proc in psutil.process_iter(['name']):
    if proc.info['name'] and 'brave' in proc.info['name'].lower():
        print("WARNING: Brave is already running! Close all Brave windows first.")

with sync_playwright() as p:
    def handle_download(download):
        download_path = os.path.join(download_folder, download.suggested_filename)
        print(f"Download starting: {download.suggested_filename}")
        download.save_as(download_path)
        print(f"Download completed: {download_path}")

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

    page.add_init_script("""
    (function () {
      function beepContinuous(duration = 5000, frequency = 600, volume = 1) {
        const AudioContextRef = window.AudioContext || window.webkitAudioContext;
        if (!AudioContextRef) return;
        const audioCtx = new AudioContextRef();
        const oscillator = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioCtx.destination);

        oscillator.type = 'sine';
        oscillator.frequency.value = frequency;
        gainNode.gain.value = volume;

        if (audioCtx.state === 'suspended') {
          audioCtx.resume();
        }

        oscillator.start();
        setTimeout(() => {
          oscillator.stop();
          audioCtx.close();
        }, duration);
      }

      function isCloudflareDialogPresent() {
        return document.querySelector('#cf-chl-widget-hr58m_response') !== null;
      }

      let alreadyBeeped = false;
      setInterval(() => {
        try {
          if (!alreadyBeeped && isCloudflareDialogPresent()) {
            alreadyBeeped = true;
            try { beepContinuous(5000, 600, 1); } catch (e) {}
            console.log('CF_TURNSTILE_DETECTED');
          } else if (alreadyBeeped && !isCloudflareDialogPresent()) {
            alreadyBeeped = false;
          }
        } catch (e) {}
      }, 1000);
    })();
    """)

    def on_console(msg):
        try:
            if msg.type == 'log' and 'CF_TURNSTILE_DETECTED' in (msg.text or ''):
                winsound.Beep(1000, 5000)
        except Exception:
            pass

    page.on('console', on_console)

    def wait_for_visible_turnstile(page, timeout_seconds=90):
        start = time.time()
        locator = page.locator("iframe[src*='challenges.cloudflare.com']").first
        while time.time() - start < timeout_seconds:
            try:
                if locator.is_visible():
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    image_files = []
    for file in os.listdir(images_folder):
        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
            image_files.append(os.path.join(images_folder, file))
    
    if not image_files:
        print("No images found in 'images' folder!")
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
                print(f"Image '{image_path}' not found!")
                continue

            upload_input = page.query_selector("input[type='file']")
            if upload_input:
                upload_input.set_input_files(image_path)
                print("Image uploaded")
            else:
                print("Upload input not found")
                continue

            time.sleep(15)

            prompt_box = page.query_selector("textarea, input[type='text']")
            if prompt_box:
                prompt_box.fill(prompt_text)
                print("Prompt filled")
            else:
                print("Prompt box not found")
                continue

            selected = False
            for btn in page.query_selector_all("button"):
                if btn.inner_text().strip() == "540P":
                    btn.click()
                    selected = True
                    print("540P selected")
                    break
            if not selected:
                print("540P button not found")
                continue

            time.sleep(1)

            generate_btn = page.query_selector("button:has-text('Generate'), button:has-text('Create')")
            if generate_btn:
                print("Clicking Generate...")
                generate_btn.click()
            else:
                print("Generate button not found")
                continue

            try:
                if wait_for_visible_turnstile(page, timeout_seconds=120):
                    print("Cloudflare Turnstile visible! Beep...")
                    winsound.Beep(1000, 5000)
                else:
                    print("No visible Turnstile check this time.")
            except Exception:
                print("No visible Turnstile check this time.")

            print("Waiting for processing to complete...")
            
            try:
                download_button = page.wait_for_selector(
                    'button.z-0.group.relative.inline-flex.items-center.justify-center.box-border.appearance-none.select-none.whitespace-nowrap.font-normal.subpixel-antialiased.overflow-hidden.tap-highlight-transparent', 
                    timeout=300000,
                    state='visible'
                )
                
                if download_button:
                    print("Processing complete! Download button appeared.")
                    print("Clicking download button...")
                    
                    with page.expect_download() as download_info:
                        download_button.click()
                    
                    download = download_info.value
                    download_path = os.path.join(download_folder, download.suggested_filename)
                    download.save_as(download_path)
                    print(f"Download completed: {download_path}")
                    
                else:
                    print("Download button not found within timeout")
                    continue
                    
            except Exception as e:
                print(f"Error waiting for/downloading: {e}")
                continue

            try:
                dest = os.path.join(processed_folder, image_name)
                shutil.move(image_path, dest)
                print(f"Moved processed image to: {dest}")
            except Exception as move_err:
                print(f"Could not move image, trying delete: {move_err}")
                try:
                    os.remove(image_path)
                    print(f"Deleted processed image: {image_path}")
                except Exception as del_err:
                    print(f"Failed to delete processed image: {del_err}")

            print(f"Completed processing for {image_name}")
            time.sleep(3)

        except Exception as e:
            print(f"Error processing {image_name}: {e}")
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
        print("No files found in download folder")

    print("\nClosing browser...")
    browser.close()
    print("Browser closed. All images processed!")
