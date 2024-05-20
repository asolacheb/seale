#pip install streamlit yfinance pandas tabulate google.generativeai datetime python-dotenv 
import os
import streamlit as st
import yfinance as yf
import pandas as pd
from tabulate import tabulate
import google.generativeai as genai
import datetime
import time
import re
from dotenv import load_dotenv

#genai_api_key = os.getenv('GENAI_API_KEY')
#genai.configure(api_key=genai_api_key)
load_dotenv()

def model_setup(company_name):
    today = datetime.datetime.now()
    month = today.strftime("%B")
    year = today.strftime("%Y")

    genai_api_key = os.getenv('GENAI_API_KEY')
    genai.configure(api_key="AIzaSyCkl3V1oMdQ4yCB2BW0_aGqLU-LOUGU22w")


    generation_config = {
      "temperature": 0.9,
      "top_p": 1,
      "top_k": 1,
      "max_output_tokens": 2048,
    }

    safety_settings = [
      {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
      },
      {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
      },
      {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
      },
      {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
      },
    ]

    model = genai.GenerativeModel(model_name="gemini-1.0-pro",
                                  generation_config=generation_config,
                                  safety_settings=safety_settings)

    convo = model.start_chat(history=[
    {
        "role": "user",
        "parts": [f"As 'Comp Finder', your primary task is to assist investment bankers by identifying 50 public comparable companies (comps) for {company_name}"]
    },
    {
        "role": "model",
        "parts": [f"The ticker should be using the yahoo format and only return the following data with the following format Ticker|Subindustry"]
    },
    ])

    convo.send_message("YOUR_USER_INPUT")
    comps = convo.last.text
    print (comps)
    return comps

def clean_df(comps):
    # Split the input text into lines
    rows = comps.strip().splitlines()

    # Attempt to find the header row with columns
    header_line = None
    for line in rows:
        if '|' in line:
            header_line = line
            break
    
    if not header_line:
        raise ValueError("No valid header found with '|' delimiters")

    # Extract column names
    columns = [col.strip() for col in re.findall(r'\|([^|]+)', header_line)]

    # Check for 'Ticker' and 'Subindustry' columns
    if 'Ticker' not in columns or 'Subindustry' not in columns:
        raise ValueError("The data returned did not contain required 'Ticker' and 'Subindustry' columns.")

    # Initialize list to store data rows
    data = []
    for row in rows:
        # Extract data from rows containing '|' delimiters and matching the header format
        if '|' in row and len(re.findall(r'\|([^|]+)', row)) == len(columns):
            row_data = re.findall(r'\|([^|]+)', row)
            data.append([item.strip() for item in row_data])

    # Create DataFrame from extracted data
    df = pd.DataFrame(data, columns=columns)

    # Standardize column names
    expected_columns = {'Ticker': 'Ticker', 'Subindustry': 'Subindustry'}
    df.columns = [expected_columns.get(col, col) for col in df.columns]

    # Ensure all expected columns are present
    for col in expected_columns.values():
        if col not in df.columns:
            df[col] = None
    
    return df

def fetch_financials(ticker):
    try:
        if not ticker:
            return None

        stock = yf.Ticker(ticker)
        info = stock.info

        if 'quoteType' not in info:
            return None

        market_cap = info.get('marketCap', 0) / 1e6  # Convert to millions
        enterprise_value = info.get('enterpriseValue', 0) / 1e6  # Convert to millions
        revenue = info.get('totalRevenue', 0) / 1e6  # Convert to millions
        ebitda = info.get('ebitda', 0) / 1e6  # Convert to millions
        company_name = info.get('longName', 'N/A')

        financials = {
            'Company Name': company_name,
            'Market Cap (USD)': f"{market_cap:.2f}M",
            'Enterprise Value (USD)': f"{enterprise_value:.2f}M",
            'Revenue (USD)': f"{revenue:.2f}M",
            'EBITDA': f"{ebitda:.2f}M"
        }
        return financials
    except Exception as e:
        return None

def calculate_ratios(financials):
    revenue = float(financials['Revenue (USD)'][:-1])  # Remove the 'M'
    ebitda = float(financials['EBITDA'][:-1])  # Remove the 'M'
    ev = float(financials['Enterprise Value (USD)'][:-1])  # Remove the 'M'

    ebitda_margin = (ebitda / revenue * 100) if revenue else 0
    ev_ebitda = (ev / ebitda) if ebitda else 0
    ev_revenue = (ev / revenue) if revenue else 0

    ratios = {
        'EBITDA Margin (%)': f"{ebitda_margin:.2f}%",
        'EV/EBITDA': f"{ev_ebitda:.2f}x",
        'EV/Revenue': f"{ev_revenue:.2f}x"
    }
    return ratios

def run_analysis(company_name):
    comps = model_setup(company_name)
    df = clean_df(comps)

    if 'Ticker' not in df.columns:
        raise ValueError("The data returned did not contain a 'Ticker' column.")

    all_data = []
    for index, row in df.iterrows():
        ticker = row['Ticker']
        if ticker and ticker != 'Private':
            financials = fetch_financials(ticker)
            if financials and not '0.00M' in financials.values():
                ratios = calculate_ratios(financials)
                if ratios:
                    data = [financials['Company Name'], ticker, row['Subindustry']] + list(financials.values())[1:] + list(ratios.values())
                    all_data.append(data)

    headers = ["Company Name", "Ticker", "Subindustry", "Market Cap (USD)", "Enterprise Value (USD)", "Revenue (USD)", "EBITDA", "EBITDA Margin (%)", "EV/EBITDA", "EV/Revenue"]
    df_display = pd.DataFrame(all_data, columns=headers)
    return df_display

def main():
    st.markdown(
        """
        <style>
        .stApp {
            text-color:black;
            background-color: white;
            secondary-background-color:#D2D2D2;
        }
        .logo-img {
            width: 50%; 
            height: auto;
        }
        .primary-color {
            color: #183968;
        }     
        .stButton>button {
            background-color: #183968;
            color: white;
        }
        .stButton>button:hover {
            background-color: white;
            color: #183968;
            border: 2px solid #183968;
        }    
        .stTextInput>div>div>input:focus {
            border-color: #007bff !important;
        }       
        </style>
        """,
        unsafe_allow_html=True
    )
    st.markdown('<img src="https://raw.githubusercontent.com/asolacheb/seale/98df77634322a8b5fe8937d95b2f2530b000b808/assets/logo.png" class="logo-img">', unsafe_allow_html=True)    
    st.markdown('<h1 class="primary-color">Seale Comp Finder</h1>', unsafe_allow_html=True)
    company_name = st.text_input("",placeholder="Enter a brief description")
    submit_button = st.form_submit_button(label='Submit')

    if submit_button or company_name:
        st.session_state['company_name'] = company_name
        max_retries = 10
        retry_delay = 5  # seconds

        if company_name:
            for attempt in range(max_retries):
                try:
                    df_display = run_analysis(company_name)
                    st.table(df_display)
                    break  # Exit loop if successful
                except Exception as e:
                    time.sleep(retry_delay)
            else:
                st.error("Failed to fetch data after several attempts. Please try again later.")

if __name__ == "__main__":
    main()