import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import threading
import time
import pandas as pd
import os
import traceback

class GMapScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Google Maps Bulk Scraper (v2.3) - LalitGeek")
        self.root.geometry("850x750")
        self.root.configure(bg="#2c3e50")

        self.is_running = False
        self.results = []
        
        # Styles
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background="#2c3e50")
        self.style.configure("TLabel", background="#2c3e50", foreground="#ecf0f1", font=("Helvetica", 10))
        self.style.configure("TCheckbutton", background="#2c3e50", foreground="#ecf0f1")
        self.style.configure("Header.TLabel", font=("Helvetica", 16, "bold"), foreground="#3498db")
        self.style.configure("TButton", font=("Helvetica", 10, "bold"))

        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        header = ttk.Label(main_frame, text="Google Maps Scraper - Pro", style="Header.TLabel")
        header.pack(pady=(0, 20))

        # Input Area
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=10)

        ttk.Label(input_frame, text="Search Query:").pack(anchor=tk.W)
        self.query_entry = ttk.Entry(input_frame, font=("Helvetica", 11))
        self.query_entry.pack(fill=tk.X, pady=5, padx=2)
        self.query_entry.insert(0, "Hospitals in Mumbai")

        # Config Frame
        config_frame = ttk.Frame(input_frame)
        config_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(config_frame, text="Max Results:").pack(side=tk.LEFT)
        self.limit_entry = ttk.Entry(config_frame, width=8)
        self.limit_entry.pack(side=tk.LEFT, padx=10)
        self.limit_entry.insert(0, "30")

        self.headless_var = tk.BooleanVar(value=False)
        self.headless_check = ttk.Checkbutton(config_frame, text="Headless Mode", variable=self.headless_var)
        self.headless_check.pack(side=tk.LEFT, padx=20)

        # Control Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        self.start_btn = ttk.Button(btn_frame, text="Start Scraping", command=self.start_scraping)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop_scraping, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.export_btn = ttk.Button(btn_frame, text="Export to CSV", command=self.export_data, state=tk.DISABLED)
        self.export_btn.pack(side=tk.RIGHT, padx=5)

        # Progress
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.status_label = ttk.Label(main_frame, text="Status: Ready")
        self.status_label.pack(anchor=tk.W, pady=5)

        # Results Table
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("Name", "Address", "Phone", "Website")
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings')
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150 if col != "Address" else 300)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def start_scraping(self):
        query = self.query_entry.get().strip()
        limit = self.limit_entry.get().strip()
        if not query:
            messagebox.showwarning("Warning", "Please enter a search query.")
            return
        
        try:
            self.max_results = int(limit)
        except:
            self.max_results = 20

        self.is_running = True
        self.results = []
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.export_btn.config(state=tk.DISABLED)
        self.progress.pack(fill=tk.X, pady=5)
        self.progress.start()
        
        threading.Thread(target=self.scrape_worker, args=(query,), daemon=True).start()

    def stop_scraping(self):
        self.is_running = False
        self.status_label.config(text="Status: Stopping...")

    def scrape_worker(self, query):
        options = Options()
        if self.headless_var.get():
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--lang=en")
        options.add_argument("--disable-notifications")
        options.add_argument("--window-size=1920,1080")

        driver = None
        try:
            try:
                driver = webdriver.Chrome(options=options)
            except:
                driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            
            driver.get("https://www.google.com/maps?hl=en")
            self.root.after(0, lambda: self.status_label.config(text="Status: Checking for consent dialog..."))
            
            # Handle Consent Dialog (Cookie popup)
            try:
                # Common "Accept all" button selectors
                consent_selectors = [
                    '//form//button[contains(@aria-label, "Accept")]',
                    '//button[contains(span, "Accept all")]',
                    '//button[contains(text(), "I agree")]'
                ]
                for selector in consent_selectors:
                    buttons = driver.find_elements(By.XPATH, selector)
                    if buttons:
                        buttons[0].click()
                        time.sleep(2)
                        break
            except: pass

            self.root.after(0, lambda: self.status_label.config(text="Status: Searching..."))
            
            # Initial search with multiple selector attempts
            search_box = None
            search_selectors = [
                (By.ID, "searchboxinput"),
                (By.NAME, "q"),
                (By.XPATH, '//input[@aria-label="Search Google Maps"]')
            ]
            
            for by, value in search_selectors:
                try:
                    search_box = WebDriverWait(driver, 10).until(EC.presence_of_element_located((by, value)))
                    if search_box: break
                except: continue
                
            if not search_box:
                # Take screenshot for debugging
                driver.save_screenshot("error_screenshot.png")
                raise Exception("Could not find the search box. See error_screenshot.png")

            search_box.send_keys(query)
            search_box.send_keys(Keys.ENTER)
            time.sleep(5)

            processed_names = set()
            found_count = 0

            while self.is_running and found_count < self.max_results:
                # Broad result selector
                containers = driver.find_elements(By.CSS_SELECTOR, "div.Nv2Ybe, div.m67qEc, div.Ua9Oge")
                if not containers:
                    containers = driver.find_elements(By.XPATH, '//div[@role="article"] | //a[contains(@href, "/maps/place/")]')

                if not containers:
                    self.root.after(0, lambda: self.status_label.config(text="Status: Finding results..."))
                    time.sleep(2)
                    continue

                for container in containers:
                    if not self.is_running or found_count >= self.max_results:
                        break
                    
                    try:
                        # Try to find the name/link
                        link = None
                        if container.tag_name == "a":
                            link = container
                        else:
                            try:
                                link = container.find_element(By.CSS_SELECTOR, "a.hfpxzc")
                            except:
                                link = container.find_element(By.XPATH, './/a[contains(@href, "/maps/place/")]')
                        
                        name = link.get_attribute("aria-label") or link.text
                        if not name or name in processed_names:
                            continue
                        
                        processed_names.add(name)
                        
                        # Scroll and click
                        driver.execute_script("arguments[0].scrollIntoView(true);", link)
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", link)
                        time.sleep(4)

                        # Extract details
                        address, phone, website = "N/A", "N/A", "N/A"

                        try:
                            addr_xpath = '//button[contains(@aria-label, "Address")] | //div[contains(@aria-label, "Address")]'
                            addr_elem = driver.find_elements(By.XPATH, addr_xpath)
                            if addr_elem:
                                address = addr_elem[0].text.strip().replace("\n", " ")
                                if not address:
                                    address = addr_elem[0].get_attribute("aria-label").replace("Address: ", "")
                        except: pass

                        try:
                            phone_xpath = '//button[contains(@aria-label, "Phone")] | //div[contains(@aria-label, "Phone")]'
                            phone_elem = driver.find_elements(By.XPATH, phone_xpath)
                            if phone_elem:
                                phone = phone_elem[0].text.strip().replace("\n", " ")
                                if not phone:
                                    phone = phone_elem[0].get_attribute("aria-label").replace("Phone: ", "")
                        except: pass

                        try:
                            web_elem = driver.find_elements(By.XPATH, '//a[contains(@data-item-id, "authority")] | //a[contains(@aria-label, "Website")]')
                            if web_elem:
                                website = web_elem[0].get_attribute("href")
                        except: pass

                        if address == "" or address == " ": address = "N/A"
                        if phone == "" or phone == " ": phone = "N/A"

                        self.results.append({"Name": name, "Address": address, "Phone": phone, "Website": website})
                        found_count += 1
                        
                        self.root.after(0, lambda n=name, a=address, p=phone, w=website: self.tree.insert("", tk.END, values=(n, a, p, w)))
                        self.root.after(0, lambda c=found_count: self.status_label.config(text=f"Status: Found {c}/{self.max_results} results"))

                    except Exception as e:
                        pass

                # Scroll results pane
                try:
                    scroll_pane = driver.find_element(By.XPATH, '//div[@role="feed" or contains(@aria-label, "Results for")]')
                    driver.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', scroll_pane)
                    time.sleep(2)
                except:
                    break

        except Exception as e:
            error_msg = f"{e}\n\n{traceback.format_exc()}"
            with open("scraper_error.log", "w") as f: f.write(error_msg)
            if driver: driver.save_screenshot("error_screenshot.png")
            self.root.after(0, lambda: messagebox.showerror("Fatal Error", f"Scraper error: {e}\n\nScreenshot saved."))
        finally:
            if driver:
                try: driver.quit()
                except: pass
            self.root.after(0, self.cleanup_ui)

    def cleanup_ui(self):
        self.is_running = False
        self.progress.stop()
        self.progress.pack_forget()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        if self.results:
            self.export_btn.config(state=tk.NORMAL)
        self.status_label.config(text=f"Status: Finished. Collected {len(self.results)} items.")

    def export_data(self):
        if not self.results: return
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if file_path:
            pd.DataFrame(self.results).to_csv(file_path, index=False)
            messagebox.showinfo("Success", "Data exported.")

if __name__ == "__main__":
    root = tk.Tk()
    app = GMapScraperApp(root)
    root.mainloop()
