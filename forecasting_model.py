# forecasting_model.py

import yfinance as yf
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
from datetime import date, timedelta

# Import your sentiment analysis function to get the sentiment data
from sentiment_analyzer import load_financial_data, extract_text_for_sentiment, get_sentiment_pipeline, analyze_sentiment

def fetch_stock_data(ticker, start_date, end_date):
    """
    Fetches historical stock data from Yahoo Finance.
    """
    try:
        data = yf.download(ticker, start=start_date, end=end_date)
        if data.empty:
            print(f"❌ No data found for ticker: {ticker}")
            return None
        print(f"✅ Successfully fetched historical data for {ticker} from {start_date} to {end_date}.")
        return data
    except Exception as e:
        print(f"❌ Error fetching stock data: {e}")
        return None

def main():
    # --- Part 1: Data Acquisition and Integration ---
    ticker = 'MMM'  # 3M Company, matching our financial documents
    start_date = '2015-01-01'
    end_date = date.today().strftime('%Y-%m-%d')
    
    # Fetch historical stock data
    stock_df = fetch_stock_data(ticker, start_date, end_date)
    
    if stock_df is None:
        return

    # Load and process your sentiment data
    raw_df = load_financial_data()
    if raw_df is None:
        return

    processed_df = extract_text_for_sentiment(raw_df)
    sentiment_pipeline = get_sentiment_pipeline()
    sentiment_df = analyze_sentiment(processed_df, sentiment_pipeline)

    # Convert sentiment data to a format that can be merged with stock data
    # Here, we'll assume a simple mapping from sentiment to a numerical score
    sentiment_df['sentiment_numeric'] = sentiment_df['sentiment_label'].apply(
        lambda x: 1 if x == 'POSITIVE' else (-1 if x == 'NEGATIVE' else 0)
    )

    # The actual date of the document is not in the 'sentiment_df',
    # but we'll simulate a merge for demonstration.
    # A real model would need a more robust way to align dates.
    # For now, let's just use the average sentiment score for the entire period.
    average_sentiment = sentiment_df['sentiment_numeric'].mean()
    stock_df['sentiment_score'] = average_sentiment

    # --- Part 2: Feature Engineering and Model Training ---
    # Create features for our model
    stock_df['day_of_week'] = stock_df.index.dayofweek
    stock_df['day_of_year'] = stock_df.index.dayofyear
    stock_df['month'] = stock_df.index.month
    stock_df['week_of_year'] = stock_df.index.isocalendar().week.astype(int)
    
    # We will use 'Open' price and 'sentiment_score' to predict 'Close' price
    features = ['Open', 'sentiment_score', 'day_of_week', 'day_of_year', 'month', 'week_of_year']
    target = 'Close'

    # Drop rows with missing values
    stock_df.dropna(inplace=True)
    
    X = stock_df[features]
    y = stock_df[target]

    # Split data for training and testing
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train a Linear Regression model
    model = LinearRegression()
    model.fit(X_train, y_train)
    
    print(f"✅ Model trained with {len(X_train)} training samples")
    print(f"📊 Features used: {', '.join(features)}")

    # Evaluate the model
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    print(f"\n✅ Model trained successfully. Mean Squared Error: {mse:.2f}")

    # --- Part 3: Forecasting ---
    # Predict the closing price for the next business day
    last_day = stock_df.index[-1]
    next_day_date = last_day + timedelta(days=1)
    
    # Create input data for the next day's prediction
    last_open = stock_df['Open'].iloc[-1]  # Keep as pandas scalar
    next_day_features = pd.DataFrame([{
        'Open': last_open,
        'sentiment_score': average_sentiment,
        'day_of_week': next_day_date.dayofweek,
        'day_of_year': next_day_date.timetuple().tm_yday,
        'month': next_day_date.month,
        'week_of_year': next_day_date.isocalendar().week
    }])
    
    # Ensure the features are in the same order as training
    prediction_input = next_day_features[features]
    predicted_close = float(model.predict(prediction_input)[0])  # Convert to float immediately
    
    print(f"\n🔮 Predicted closing price for the next trading day: ${predicted_close:.2f}")
    print(f"📊 Last actual closing price: ${float(stock_df['Close'].iloc[-1]):.2f}")
    print(f"📈 Current sentiment score: {average_sentiment:.3f}")
    
    # Calculate prediction direction
    last_close = float(stock_df['Close'].iloc[-1])
    direction = "📈 UP" if predicted_close > last_close else "📉 DOWN"
    change_pct = ((predicted_close - last_close) / last_close) * 100
    print(f"🎯 Prediction direction: {direction} ({change_pct:+.2f}%)")
    
    # Display model feature importance
    try:
        feature_importance = pd.DataFrame({
            'feature': features,
            'coefficient': model.coef_.flatten()  # Flatten to ensure 1D array
        }).sort_values('coefficient', key=abs, ascending=False)
        
        print(f"\n🔍 Model Feature Importance:")
        for _, row in feature_importance.iterrows():
            print(f"  {row['feature']}: {row['coefficient']:.4f}")
    except Exception as e:
        print(f"\n⚠️ Could not display feature importance: {e}")
        print(f"🔍 Model coefficients: {model.coef_}")

if __name__ == "__main__":
    main()