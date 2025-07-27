async function fetchData(year) {
    const response = await fetch(`/analyze_data/${year}`);
    return await response.json();
}

async function renderCharts() {
    const year = document.getElementById("year").value;
    const data = await fetchData(year);

    updateCategoryChart(categoryChart, Object.keys(data.category_count), Object.values(data.category_count));
    updateCountryChart(countryChart, Object.values(data.country_count));
}

function updateCategoryChart(chart, labels, data) {
    chart.data.labels = labels;
    chart.data.datasets[0].data = data;

    chart.update();
}

function updateCountryChart(chart, countryData) {
    // データをオブジェクトから配列に変換
    const labelsCountry = Object.keys(countryData).map(key => countryData[key].country);
    const dataCountry = Object.values(countryData).map(item => item.count);

    chart.data.labels = labelsCountry;
    chart.data.datasets[0].data = dataCountry;

    // データの数だけ背景色を生成
    const backgroundColors = generateColors(labelsCountry.length);
    chart.data.datasets[0].backgroundColor = backgroundColors;

    chart.update();
}

let colorIndex = 0;

// 順番に背景色を生成する関数
function generateColors(numColors) {
    const colors = [];
    const availableColors = [
        'rgba(255, 99, 132, 0.6)',
        'rgba(54, 162, 235, 0.6)',
        'rgba(255, 206, 86, 0.6)',
        'rgba(75, 192, 192, 0.6)',
        'rgba(153, 102, 255, 0.6)',
        'rgba(255, 159, 64, 0.6)',
        'rgba(144, 238, 144, 0.6)',
        'rgba(255, 182, 193, 0.6)',
        'rgba(173, 216, 230, 0.6)',
        'rgba(240, 230, 140, 0.6)',
        'rgba(220, 220, 220, 0.6)',
        'rgba(205, 92, 92, 0.6)',
        'rgba(255, 0, 255, 0.6)',
        'rgba(0, 255, 255, 0.6)',
        'rgba(128, 0, 128, 0.6)',
        'rgba(0, 128, 0, 0.6)',
        'rgba(0, 0, 128, 0.6)',
        'rgba(218, 112, 214, 0.6)',
        'rgba(72, 61, 139, 0.6)',
        'rgba(107, 142, 35, 0.6)'
    ];

    for (let i = 0; i < numColors; i++) {
        colors.push(getColor());
    }
    return colors;

    function getColor() {
        const color = availableColors[colorIndex % availableColors.length];
        colorIndex++;
        return color;
    }
}

const ctxCategoryElement = document.getElementById('categoryChart')
const ctxCountryElement = document.getElementById('countryChart')

const ctxCategory = ctxCategoryElement ? ctxCategoryElement.getContext('2d') : null;
const ctxCountry = ctxCountryElement ? ctxCountryElement.getContext('2d') : null;

const categoryChart = new Chart(ctxCategory, {
    type: 'bar',
    data: { labels: [], datasets: [{ label: 'team(s)', data: [], backgroundColor: 'rgb(255, 100, 23)' }] },
    options: {
        scales: {
            y: {
                beginAtZero: true
            }
        }
    }
});

const countryChart = new Chart(ctxCountry, {
    type: 'pie',
    data: {
        labels: [],
        datasets: [{
            label: 'team(s)',
            data: [],
            backgroundColor: []
        }]
    },
    options: {
        responsive: true,
    }
});


// 初回ロード時に最新年を表示
renderCharts();
