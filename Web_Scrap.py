import pandas as pd
import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import mysql.connector as sql
import time
import os

# Set up Streamlit interface
st.title("E-commerce Product Scraper")

# User inputs for web scraping
base_url = st.text_input("Enter the search URL (e.g., https://www.flipkart.com/search?q=laptop):", "")
num_pages = st.number_input("Enter the number of pages to scrape:", min_value=1, value=1)
common_selector = st.text_input("Enter the CSS selector for the common product container (e.g., div.yKfJKb.row for Flipkart):", "")
title_sub_selector = st.text_input("Enter the CSS selector for product titles within the container (e.g., div.KzDlHZ for Flipkart):", "")
price_sub_selector = st.text_input("Enter the CSS selector for product prices within the container (e.g., div.cN1yYO for Flipkart):", "")
rating_sub_selector = st.text_input("Enter the CSS selector for product ratings and reviews within the container (e.g., div._5OesEi for Flipkart):", "")

# MySQL connection details
db_host = st.text_input("Enter MySQL host (e.g., localhost):", "localhost")
db_user = st.text_input("Enter MySQL user (e.g., root):", "root")
db_password = st.text_input("Enter MySQL password:", type="password")
db_name = st.text_input("Enter MySQL database name (e.g., ecommerce_scraping):", "ecommerce_scraping")

# Excel file path
excel_file_path = st.text_input("Enter the path to save the Excel file (e.g., C:/Users/DELL/Documents/shiash project/Datas/scraped_products.xlsx):", "C:/Users/DELL/Documents/shiash project/Datas/scraped_products.xlsx")

# Set up Selenium and ChromeDriver
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

service = Service('C:/Users/DELL/Documents/shiash project/chromedriver-win32/chromedriver.exe')
driver = webdriver.Chrome(service=service, options=chrome_options)

# Function to scrape a single page
def scrape_page(driver, page_url, common_selector, title_sub_selector, price_sub_selector, rating_sub_selector):
    driver.get(page_url)
    wait = WebDriverWait(driver, 10)

    product_containers = []
    try:
        product_containers = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, common_selector)))
    except:
        st.error("Error locating product containers.")
    
    product_titles, product_prices, product_ratings = [], [], []
    
    for container in product_containers:
        try:
            title = container.find_element(By.CSS_SELECTOR, title_sub_selector).text
            product_titles.append(title)
        except:
            product_titles.append("N/A")
        
        try:
            price = container.find_element(By.CSS_SELECTOR, price_sub_selector).text
            product_prices.append(price)
        except:
            product_prices.append("N/A")
        
        try:
            rating_element = container.find_element(By.CSS_SELECTOR, rating_sub_selector)
            rating = rating_element.get_attribute('aria-label') or rating_element.text
            product_ratings.append(rating)
        except:
            product_ratings.append("N/A")
    
    return product_titles, product_prices, product_ratings

# Scraping multiple pages
def scrape_multiple_pages(base_url, num_pages, common_selector, title_sub_selector, price_sub_selector, rating_sub_selector):
    all_titles, all_prices, all_ratings = [], [], []
    
    for page_num in range(1, num_pages + 1):
        st.write(f"Scraping page {page_num}...")
        page_url = f"{base_url}&page={page_num}"
        titles, prices, ratings = scrape_page(driver, page_url, common_selector, title_sub_selector, price_sub_selector, rating_sub_selector)
        
        all_titles.extend(titles)
        all_prices.extend(prices)
        all_ratings.extend(ratings)
        time.sleep(2)
    
    return pd.DataFrame({"Title": all_titles, "Price": all_prices, "Rating": all_ratings})

# Function to save data to MySQL
def save_to_mysql(df):
    conn = sql.connect(
        host=db_host,
        user=db_user,
        password=db_password,
        database=db_name
    )
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255),
            price VARCHAR(50),
            rating VARCHAR(50)
        )
    """)

    # Insert data into the table
    for index, row in df.iterrows():
        cursor.execute("INSERT INTO products (title, price, rating) VALUES (%s, %s, %s)", (row['Title'], row['Price'], row['Rating']))

    conn.commit()
    cursor.close()
    conn.close()

# Function to save data as Excel file
def save_excel_locally(data, file_path):
    writer = pd.ExcelWriter(file_path, engine='xlsxwriter')
    data.to_excel(writer, index=False)
    writer.close()  # This replaces the deprecated save() method
    st.success(f"Data saved as Excel file at: {file_path}")

# Check if scraped data exists in session state
if 'scraped_data' not in st.session_state:
    st.session_state['scraped_data'] = None

# Scrape data button
if st.button("Scrape Data"):
    if base_url and common_selector and title_sub_selector and price_sub_selector and rating_sub_selector:
        scraped_data = scrape_multiple_pages(base_url, num_pages, common_selector, title_sub_selector, price_sub_selector, rating_sub_selector)
        st.session_state['scraped_data'] = scraped_data  # Store data in session state
        st.write(scraped_data)
    else:
        st.error("Please fill all input fields.")

# Save to MySQL button
if st.button("Save to MySQL"):
    if st.session_state['scraped_data'] is not None:
        save_to_mysql(st.session_state['scraped_data'])
        st.success("Data saved to MySQL.")
    else:
        st.error("No data to save. Please scrape data first.")

# Save Excel locally button
if st.button("Save Excel Locally"):
    if st.session_state['scraped_data'] is not None:
        # Save the Excel file to the given path
        save_excel_locally(st.session_state['scraped_data'], excel_file_path)
    else:
        st.error("No data to save. Please scrape data first.")

# Close the driver when done
driver.quit()
