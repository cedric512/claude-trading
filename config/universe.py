"""
S&P 500 + Nasdaq 100 investable universe, organised by sector.
Covers ~150 high-liquidity names that form the screening pool.
"""

UNIVERSE: dict[str, list[str]] = {
    "Technology": [
        "AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CRM", "AMD", "QCOM",
        "TXN", "AMAT", "LRCX", "KLAC", "ADI", "MU", "MRVL", "NXPI",
        "CDNS", "SNPS", "ANSS", "FTNT", "PANW", "CRWD", "ZS", "DDOG",
        "TEAM", "WDAY", "ADBE", "INTU", "NOW", "CSCO", "IBM", "ACN",
        "INTC", "HPQ", "DELL", "STX", "WDC", "ON",
    ],
    "Communication Services": [
        "GOOGL", "META", "NFLX", "DIS", "CMCSA", "T", "VZ", "TMUS",
        "CHTR", "TTWO", "EA", "WBD", "SNAP", "PINS",
    ],
    "Consumer Discretionary": [
        "AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "TGT", "LOW",
        "BKNG", "ABNB", "CMG", "GM", "F", "ORLY", "AZO", "ROST",
        "EBAY", "ETSY", "RCL", "CCL",
    ],
    "Consumer Staples": [
        "WMT", "COST", "PG", "KO", "PEP", "PM", "MO", "MDLZ",
        "GIS", "CL", "KHC", "STZ", "KDP", "MNST", "EL",
    ],
    "Healthcare": [
        "LLY", "JNJ", "UNH", "ABBV", "MRK", "TMO", "ABT", "DHR",
        "BMY", "AMGN", "GILD", "CVS", "CI", "HCA", "ISRG", "REGN",
        "VRTX", "BIIB", "IDXX", "DXCM", "ZBH", "BAX", "BDX", "SYK",
        "EW", "GEHC", "MRNA", "ILMN", "ALGN",
    ],
    "Financials": [
        "BRK-B", "JPM", "BAC", "WFC", "GS", "MS", "BLK", "C",
        "AXP", "SPGI", "MCO", "CME", "ICE", "V", "MA", "COF",
        "USB", "PNC", "TFC", "SCHW", "CB", "MET", "AIG", "PRU",
        "ALL", "AFL", "MMC", "AON",
    ],
    "Energy": [
        "XOM", "CVX", "COP", "EOG", "SLB", "PSX", "VLO", "MPC",
        "OXY", "KMI", "WMB", "DVN", "FANG", "HAL",
    ],
    "Industrials": [
        "CAT", "HON", "UPS", "BA", "RTX", "GE", "LMT", "NOC",
        "DE", "MMM", "EMR", "ETN", "PH", "ROK", "AME", "PCAR",
        "ODFL", "CSX", "NSC", "UNP", "FDX", "CTAS", "ROP",
    ],
    "Materials": [
        "LIN", "APD", "ECL", "SHW", "FCX", "NEM", "NUE", "CF",
        "MOS", "PPG", "VMC", "MLM",
    ],
    "Real Estate": [
        "AMT", "PLD", "EQIX", "CCI", "PSA", "O", "DLR", "WELL",
        "SPG", "AVB",
    ],
    "Utilities": [
        "NEE", "DUK", "SO", "AEP", "EXC", "D", "SRE", "PCG",
        "XEL", "ED",
    ],
}

# Flat list of all tickers
ALL_TICKERS: list[str] = [t for tickers in UNIVERSE.values() for t in tickers]

# Reverse map: ticker -> sector
TICKER_SECTOR: dict[str, str] = {
    ticker: sector
    for sector, tickers in UNIVERSE.items()
    for ticker in tickers
}

# Benchmark
BENCHMARK = "SPY"
QQQ = "QQQ"
