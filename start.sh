#!/bin/bash
set -e

# Start Streamlit on port 8080
streamlit run app.py --server.port 8080 --browser.gatherUsageStats false &
STREAMLIT_PID=$!

# Start proxy: port 5000 -> 8080 (immediately so Replit detects port 5000)
python proxy.py &
PROXY_PID=$!

# Keep running until Streamlit exits
wait $STREAMLIT_PID
kill $PROXY_PID 2>/dev/null
