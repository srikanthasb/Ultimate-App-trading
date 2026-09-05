from src.data.market_data import get_market_data
from src.analysis.indicators import add_indicators
from src.analysis.snapshot import create_market_snapshot


data = get_market_data(
    ticker="TCS.NS",
    period="6mo",
    interval="1d",
)

data = add_indicators(data)

snapshot = create_market_snapshot(
    data=data,
    symbol="TCS.NS",
)

print("\nMARKET SNAPSHOT")
print("----------------")

for key, value in snapshot.items():
    print(f"{key}: {value}")