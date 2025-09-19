document.addEventListener("DOMContentLoaded", () => {
    const container = document.querySelector(".main-container");
    const instrumentKey = container.dataset.instrument;
    const historicalData = Array.isArray(container.dataset.historical)
        ? container.dataset.historical
        : JSON.parse(container.dataset.historical || "[]");
    const historicalAlerts = Array.isArray(container.dataset.alerts)
        ? container.dataset.alerts
        : JSON.parse(container.dataset.alerts || "[]");

    let alertMarkers = [];

    const chartOptions = { 
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
        alertMarkers.push({
            time,
            position: type === "BUY" ? "aboveBar" : "belowBar",
            color: type === "BUY" ? "#26a69a" : "#ef5350",
            shape: type === "BUY" ? "arrowUp" : "arrowDown",
            text
        });
        LightweightCharts.createSeriesMarkers(volumeCandles, alertMarkers);
    }

    function mapCandleData(data, key) {
        return data
            .filter(d => d[key] && d[key].open != null)
            .map(d => ({
                time: d.price.time,
                open: parseFloat(d[key].open),
                high: parseFloat(d[key].high),
                low: parseFloat(d[key].low),
                close: parseFloat(d[key].close)
            }));
    }

    candleSeries.setData(mapCandleData(historicalData, "price"));
    volumeCandles.setData(mapCandleData(historicalData, "volume"));

    historicalAlerts.forEach(alert => {
        addAlertMarker(alert.time, alert.text, alert.signal);
    });

    const ws = new WebSocket(`ws://${window.location.host}/ws/live/${instrumentKey}`);
    ws.onmessage = (event) => {
        const tick = JSON.parse(event.data);

        if (tick.alert) {
            addAlertMarker(tick.price.time, tick.alert.text, tick.alert.signal);
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