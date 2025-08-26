document.addEventListener("DOMContentLoaded", () => {
    const container = document.querySelector(".main-container");
    const instrumentKey = container.dataset.instrument;

    const historicalData = JSON.parse(container.dataset.historical);
    const historicalAlerts = JSON.parse(container.dataset.alerts);

    // Keep a global array of alert markers
    let alertMarkers = [];

    let chartOptions = { 
        layout: { 
            textColor: 'white', 
            background: { type: 'solid', color: 'rgba(0,0,0,0)' }
        },
        grid: {
            vertLines: { color: 'rgba(255,255,255,0.1)' },
            horzLines: { color: 'rgba(255,255,255,0.1)' }
        },
        timeScale: { timeVisible: true, secondsVisible: false }
    };

    const priceChart = LightweightCharts.createChart(
        document.getElementById('live-chart'), chartOptions
    );
    const candleSeries = priceChart.addSeries(LightweightCharts.CandlestickSeries, { 
        upColor: '#26a69a', downColor: '#ef5350',
        borderUpColor: '#26a69a', borderDownColor: '#ef5350',
        wickUpColor: '#26a69a', wickDownColor: '#ef5350'
    });

    priceChart.timeScale().fitContent();

    const volumeChart = LightweightCharts.createChart(
        document.getElementById('volume-chart'), chartOptions
    );

    const volumeCandles = volumeChart.addSeries(LightweightCharts.CandlestickSeries, { 
        upColor: '#26a69a', downColor: '#ef5350',
        borderVisible: false,
        wickUpColor: '#26a69a', wickDownColor: '#ef5350'
    });

    volumeChart.timeScale().fitContent();

    function addAlertMarker(time, text, type = "up") {
        console.log(time, text, type);
        
        alertMarkers.push({
            time: time, 
            position: type === "BUY" ? "aboveBar" : "belowBar",
            color: type === "BUY" ? "#26a69a" : "#ef5350",
            shape: type === "BUY" ? "arrowUp" : "arrowDown",
            text: text
        });
        LightweightCharts.createSeriesMarkers(volumeCandles, alertMarkers)
    }

    // Load historical data
    const priceCandles = historicalData
        .filter(d => d.price && d.price.open != null)
        .map(d => ({
            time: d.price.time,
            open: parseFloat(d.price.open),
            high: parseFloat(d.price.high),
            low: parseFloat(d.price.low),
            close: parseFloat(d.price.close)
        }));
    candleSeries.setData(priceCandles);

    const volumeCandlesData = historicalData
        .filter(d => d.volume && d.volume.open != null)
        .map(d => ({
            time: d.price.time,
            open: parseFloat(d.volume.open),
            high: parseFloat(d.volume.high),
            low: parseFloat(d.volume.low),
            close: parseFloat(d.volume.close)
        }));
    volumeCandles.setData(volumeCandlesData);

    historicalAlerts.forEach(alert => {
        addAlertMarker(alert.time, alert.text, alert.signal);
    });

    // WebSocket updates
    let ws = new WebSocket(`ws://${window.location.host}/ws/live/${instrumentKey}`);
    ws.onmessage = (event) => {
        const tick = JSON.parse(event.data);

        console.log(tick);
        
        if (tick.alert) {
            addAlertMarker(tick.price.time, tick.alert.text, tick.alert.type);
        }

        candleSeries.update({
            time: tick.price.time,
            open: parseFloat(tick.price.open),
            high: parseFloat(tick.price.high),
            low: parseFloat(tick.price.low),
            close: parseFloat(tick.price.close)
        });

        volumeCandles.update({
            time: tick.price.time,
            open: parseFloat(tick.volume.open),
            high: parseFloat(tick.volume.high),
            low: parseFloat(tick.volume.low),
            close: parseFloat(tick.volume.close)
        });
    };
});
