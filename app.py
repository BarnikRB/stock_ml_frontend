import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta
import yfinance as yf
import time


# Backend API URL
API_BASE_URL = st.secrets["API_BASE_URL"]  # Change if your backend is running elsewhere


def is_valid_ticker(ticker):
    """Validates a ticker using yfinance."""
    try:
        ticker_data = yf.Ticker(ticker)
        
        # Use history() instead of info to check validity
        hist = ticker_data.history(period="1d")
        
        # If history() returns data, it's a valid ticker
        return not hist.empty
    except Exception:
        return False


def fetch_tickers():
    """Fetch the list of available tickers from the backend."""
    try:
        response = requests.get(f"{API_BASE_URL}/tickers")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching tickers: {e}")
        return []


def fetch_historical_data(ticker):
    """Fetch historical data for the given ticker from the backend."""
    try:
        response = requests.get(f"{API_BASE_URL}/historical_data/{ticker}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching historical data for {ticker}: {e}")
        return None


def fetch_predictions(ticker):
    """Fetch predictions for the given ticker from the backend."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/predict", json={"ticker": ticker}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching predictions for {ticker}: {e}")
        return None


def add_new_ticker(ticker):
    """Add a new ticker to the backend, after validating."""
    if not is_valid_ticker(ticker):
        st.error(f"Invalid ticker: {ticker}")
        return None
    try:
        response = requests.post(f"{API_BASE_URL}/add", json={"ticker": ticker})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error adding ticker {ticker}: {e}")
        return None


# Streamlit UI
st.title("Stock Price Prediction App")

# Initialize session state
if "selected_ticker" not in st.session_state:
    st.session_state["selected_ticker"] = None
if "all_tickers" not in st.session_state:
    st.session_state["all_tickers"] = []
if "ticker_added" not in st.session_state:
    st.session_state["ticker_added"] = False
    st.session_state["initial_load"] = True

# Sidebar for ticker selection and adding
# Sidebar for ticker selection and adding
with st.sidebar:
    st.header("Ticker Options")
    
    # Always fetch latest tickers when rendering sidebar
    st.session_state["all_tickers"] = fetch_tickers()
    
    if not st.session_state["all_tickers"]:
        st.warning("No tickers available. Please add a ticker.")
        st.session_state["selected_ticker"] = None
    else:
        st.session_state["selected_ticker"] = st.selectbox(
            "Select Ticker",
            options=st.session_state["all_tickers"],
            index=0 if st.session_state["all_tickers"] else None,
        )

    st.header("Add Ticker")
    new_ticker = st.text_input("Enter New Ticker")
    add_button = st.button("Add Ticker")

    if add_button and new_ticker:
        add_response = add_new_ticker(new_ticker)
        if add_response:
            st.success(add_response.get("message"))
            
            # Fetch the updated tickers list
            st.session_state["all_tickers"] = fetch_tickers()

            # Force Streamlit to re-run script so dropdown updates
            st.rerun()

if st.session_state["selected_ticker"]:
    # Fetch historical data
    historical_data = fetch_historical_data(st.session_state["selected_ticker"])

    if historical_data and historical_data.get("dates"):
        # Prepare data for plotting
        dates = pd.to_datetime(historical_data["dates"])
        close = historical_data["close"]

        df_historical = pd.DataFrame({"Date": dates, "Close": close})

        # Fetch predictions
        predictions_data = fetch_predictions(st.session_state["selected_ticker"])

        if predictions_data and predictions_data.get("predictions"):
            predictions = predictions_data["predictions"]
            # Prepare the prediction dates
            last_date = df_historical["Date"].max()
            prediction_dates = [last_date + timedelta(days=i) for i in range(1, 8)]
            df_predictions = pd.DataFrame({"Date": prediction_dates, "Close": predictions})
            # Combine historical data and predictions
            df_combined = pd.concat([df_historical, df_predictions], ignore_index=True)
            # Plot using plotly
            fig = px.line(
                df_combined,
                x="Date",
                y="Close",
                title=f"Stock Data and Prediction for {st.session_state['selected_ticker']}",
            )

            # Convert Timestamp to numerical value for vertical line
            last_date_ts = time.mktime(last_date.timetuple())

            fig.add_vline(
                x=last_date_ts * 1000,
                line_dash="dash",
                annotation_text="Today",
                annotation_position="top left",
            )  # times 1000 to change it to miliseconds
            st.plotly_chart(fig)
        else:
            # Plot the historical data
            fig = px.line(
                df_historical,
                x="Date",
                y="Close",
                title=f"Stock Data for {st.session_state['selected_ticker']}",
            )
            st.plotly_chart(fig)
    else:
        st.warning(
            "Could not retrieve data, please make sure ticker has valid historical data"
        )