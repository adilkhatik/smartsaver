#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import re
import requests
from bs4 import BeautifulSoup
import time
from smtplib import SMTP
import urllib.request
import threading
import matplotlib.pyplot as plt
from datetime import datetime
from email.mime.text import MIMEText
import numpy as np
import plotly.graph_objects as go


class ProductTracker:
    def __init__(self):
        self.user_data = {}  # Store user-specific data (desired price, alert time, tracked prices)
        self.lock = threading.Lock()

    def find_price(self, URL):
        try:
            if 'amazon' in URL:
                response = urllib.request.urlopen(URL)
                html_content = response.read().decode("utf-8")
                soup = BeautifulSoup(html_content, "html.parser")
                selected_area = soup.find(class_="a-price-whole")
                price = selected_area.get_text() if selected_area else None
                return price
            elif 'flipkart' in URL:
                response = requests.get(URL)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
                selected_area = soup.find(class_="_30jeq3 _16Jk6d")
                price = selected_area.get_text() if selected_area else None
                return price
        except Exception as e:
            print(f'An error occurred during web scraping: {e}')
            return None

    def plot_prices(self, user_email):
        if user_email in self.user_data:
            with self.lock:
                user_info = self.user_data[user_email]
                timestamps, prices = zip(*user_info['tracked_prices'])

                # Create a scatter plot with tracked prices
                trace_prices = go.Scatter(x=timestamps, y=prices, mode='markers+lines', name=f'Tracked Prices for {user_email}', marker=dict(color='blue'))

                # Plot desired price as a horizontal line
                if user_info['desired_price'] is not None:
                    desired_price = user_info['desired_price']
                    trace_desired_price = go.Scatter(x=timestamps, y=[desired_price] * len(timestamps), mode='lines', name='Desired Price', line=dict(color='red', dash='dash'))

                # Create the figure
                fig = go.Figure(data=[trace_prices, trace_desired_price] if 'trace_desired_price' in locals() else [trace_prices])

                # Customize the layout
                fig.update_layout(title=f'Price Tracking for {user_email}',
                                  xaxis_title='Time',
                                  yaxis_title='Price (in ₹)',
                                  showlegend=True,
                                  legend=dict(x=0, y=1),
                                  hovermode='closest')

                # Add hover text
                hover_text = [f'₹{price:.2f}' for price in prices]
                fig.update_traces(text=hover_text, hoverinfo='text')

                # Show the figure
                fig.show()






    def update_historical_prices(self, user_email, price):
        timestamp = datetime.now()
        with self.lock:
            if user_email not in self.user_data:
                self.user_data[user_email] = {'desired_price': None, 'alert_time': None, 'tracked_prices': []}

            self.user_data[user_email]['tracked_prices'].append((timestamp, price))

    @staticmethod
    def is_valid_email(email):
        pattern = re.compile(r"[^@]+@[^@]+\.[^@]+")
        return pattern.match(email)

    def get_user_input(self):
        while True:
            try:
                desired_price = float(input("Enter your desired price: "))
                alert_time = int(input("Enter the alert time interval (in seconds): "))
                dist_email = input("Please enter your email: ")
                if not self.is_valid_email(dist_email):
                    print("Invalid email address. Please enter a valid email.")
                    continue
                return desired_price, alert_time, dist_email
            except ValueError:
                print("Invalid input. Please enter a valid number.")

    def send_email(self, subject, body, dist_email):
        SMTP_SERVER = "smtp.gmail.com"
        PORT = 587
        EMAIL_ID = "itsmyself024@gmail.com"  # Update with your email
        PASSWORD = "odkedjlcirbxfaie"  # Update with your email password
        try:
            if not self.is_valid_email(dist_email):
                print("Invalid email address. Email not sent.")
                return

            subject_utf8 = subject.encode('utf-8')
            body_utf8 = body.encode('utf-8')

            server = SMTP(SMTP_SERVER, PORT)
            server.starttls()
            server.login(EMAIL_ID, PASSWORD)

            msg = MIMEText(body_utf8.decode('utf-8'), 'plain', 'utf-8')
            msg['Subject'] = subject_utf8.decode('utf-8')

            server.sendmail(EMAIL_ID, dist_email, msg.as_string())
            server.quit()
        except Exception as e:
            print(f"An error occurred while sending the email: {e}")

    def check_price(self, URL, desired_price, alert_time, dist_email):
        start_time = time.time()

        while True:
            price = self.find_price(URL)
            print(price)

            if price is None:
                #print(f"Invalid link for {URL}")
                break

            current_price_text = price.replace('₹', '').replace(',', '')
            current_price = float(current_price_text) if current_price_text else None

            self.update_historical_prices(dist_email, current_price)

            if desired_price is None or alert_time is None:
                # Set user-specific values for the first time
                self.user_data[dist_email]['desired_price'] = desired_price
                self.user_data[dist_email]['alert_time'] = alert_time

            if current_price and current_price <= desired_price:
                print(f"Desired price reached for {URL}! Current price: ₹{current_price}")
                subject = "BUY Now"
                body = f"Desired price reached! with price ₹{current_price} and link is {URL}"
                self.send_email(subject, body, dist_email)
                break

            elapsed_time = time.time() - start_time

            if elapsed_time >= alert_time:
                subject = "Price Alert"
                if current_price is not None:
                    body = f"Oops! The price has not changed for {URL}. Current price is ₹{current_price}. Consider buying or checking other products."
                else:
                    body = f"Oops! The price could not be fetched for {URL}. Please check the link or try again later."
                self.send_email(subject, body, dist_email)
                break

            time.sleep(10)

        # Generate a graph for the user after the tracking is over
        self.plot_prices(dist_email)

if __name__ == "__main__":
    product_tracker = ProductTracker()
    while True:
        URL = input("Enter the URL (or 'exit' to stop adding URLs): ")
        if URL.lower() == 'exit':
            break

        desired_price, alert_time, dist_email = product_tracker.get_user_input()

        thread = threading.Thread(
            target=product_tracker.check_price,
            args=(URL, desired_price, alert_time, dist_email)
        )
        thread.start()

