document.addEventListener('DOMContentLoaded', function() {

    // --- 3D Background Animation ---
    const canvas = document.getElementById('bg-canvas');
    if (canvas) {
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        const renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true });
        renderer.setSize(window.innerWidth, window.innerHeight);

        const geometry = new THREE.IcosahedronGeometry(2, 1);
        const material = new THREE.MeshStandardMaterial({
            color: 0x6366f1,
            wireframe: true,
            roughness: 0.5,
            metalness: 0.5,
        });
        const shape = new THREE.Mesh(geometry, material);
        scene.add(shape);

        const light = new THREE.DirectionalLight(0xffffff, 1);
        light.position.set(5, 5, 5);
        scene.add(light);
        
        const ambientLight = new THREE.AmbientLight(0x404040, 2);
        scene.add(ambientLight);

        camera.position.z = 5;

        function animate() {
            requestAnimationFrame(animate);
            shape.rotation.x += 0.001;
            shape.rotation.y += 0.001;
            renderer.render(scene, camera);
        }
        animate();

        window.addEventListener('resize', () => {
            renderer.setSize(window.innerWidth, window.innerHeight);
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
        });
    }


    // --- Dashboard & Charting Logic ---
    const fileInput = document.getElementById('csv-file-input');
    const charts = {};

    if (fileInput) {
        fileInput.addEventListener('change', (event) => {
            const file = event.target.files[0];
            if (file) {
                Papa.parse(file, {
                    header: true,
                    dynamicTyping: true,
                    skipEmptyLines: true,
                    complete: function(results) {
                        document.getElementById('upload-error').textContent = '';
                        processData(results.data);
                    },
                    error: function(error) {
                        document.getElementById('upload-error').textContent = 'Error parsing CSV file. Please check the format.';
                        console.error("CSV Parsing Error:", error);
                    }
                });
            }
        });
    }
    
    function processData(data) {
        const requiredColumns = ['Date', 'Product', 'Units Sold', 'Unit Price', 'Total Revenue'];
        const firstRow = data[0] || {};
        const hasAllColumns = requiredColumns.every(col => col in firstRow);

        if (!hasAllColumns) {
            document.getElementById('upload-error').textContent = `Invalid CSV. Make sure it has these columns: ${requiredColumns.join(', ')}`;
            return;
        }

        data = data.filter(row => row.Date && row['Total Revenue'] != null);
        data.forEach(row => {
            row.Date = new Date(row.Date);
        });

        document.getElementById('upload-section').classList.add('hidden');
        document.getElementById('dashboard-content').classList.remove('hidden');

        const totalRevenue = data.reduce((sum, row) => sum + row['Total Revenue'], 0);
        const totalUnits = data.reduce((sum, row) => sum + row['Units Sold'], 0);
        const totalProducts = new Set(data.map(row => row.Product)).size;

        document.getElementById('total-revenue').textContent = `$${totalRevenue.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        document.getElementById('total-units').textContent = totalUnits.toLocaleString();
        document.getElementById('total-products').textContent = totalProducts;

        Object.values(charts).forEach(chart => chart.destroy());

        const monthlySales = {};
        data.forEach(row => {
            const month = row.Date.toLocaleString('default', { month: 'short', year: '2-digit' });
            if (!monthlySales[month]) monthlySales[month] = 0;
            monthlySales[month] += row['Total Revenue'];
        });
        const sortedMonths = Object.keys(monthlySales).sort((a,b) => {
            const [mA, yA] = a.split(' ');
            const [mB, yB] = b.split(' ');
            return new Date(`01-${mA}-20${yA}`) - new Date(`01-${mB}-20${yB}`);
        });
        const sortedValues = sortedMonths.map(m => monthlySales[m]);

        charts.monthly = createChart('monthly-sales-chart', 'line', sortedMonths, sortedValues, 'Total Revenue');
        
        const productSales = {};
        data.forEach(row => {
            if (!productSales[row.Product]) productSales[row.Product] = 0;
            productSales[row.Product] += row['Total Revenue'];
        });
        charts.product = createChart('product-sales-chart', 'bar', Object.keys(productSales), Object.values(productSales), 'Total Revenue');

        data.sort((a, b) => a.Date - b.Date);
        const movingAvg = [];
        for (let i = 0; i < data.length; i++) {
            if (i < 6) movingAvg.push(null);
            else {
                const sum = data.slice(i - 6, i + 1).reduce((acc, curr) => acc + curr['Total Revenue'], 0);
                movingAvg.push(sum / 7);
            }
        }
        const dailyDates = data.map(row => row.Date.toLocaleDateString());
        const dailySales = data.map(row => row['Total Revenue']);
        charts.movingAverage = createMovingAverageChart('moving-average-chart', dailyDates, dailySales, movingAvg);
    }

    function createChart(canvasId, type, labels, data, label) {
        const ctx = document.getElementById(canvasId).getContext('2d');
        return new Chart(ctx, {
            type: type,
            data: {
                labels: labels,
                datasets: [{
                    label: label,
                    data: data,
                    backgroundColor: 'rgba(99, 102, 241, 0.6)',
                    borderColor: 'rgba(99, 102, 241, 1)',
                    borderWidth: 2,
                    fill: type === 'line' ? true : false,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { 
                        beginAtZero: true,
                        ticks: { color: '#9ca3af' },
                        grid: { color: '#374151' }
                    },
                    x: {
                        ticks: { color: '#9ca3af' },
                        grid: { color: '#374151' }
                    }
                },
                plugins: {
                    legend: {
                        labels: {
                            color: '#d1d5db'
                        }
                    }
                }
            }
        });
    }
    
    function createMovingAverageChart(canvasId, labels, dailyData, avgData) {
        const ctx = document.getElementById(canvasId).getContext('2d');
        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Daily Sales',
                    data: dailyData,
                    borderColor: 'rgba(52, 211, 153, 0.5)',
                    borderWidth: 1.5,
                    pointRadius: 0,
                }, {
                    label: '7-Day Moving Average',
                    data: avgData,
                    borderColor: 'rgba(236, 72, 153, 1)',
                    borderWidth: 2.5,
                    pointRadius: 0,
                    tension: 0.2
                }]
            },
            options: {
                 responsive: true,
                 maintainAspectRatio: false,
                 scales: {
                    y: { 
                        beginAtZero: true,
                        ticks: { color: '#9ca3af' },
                        grid: { color: '#374151' }
                    },
                    x: {
                        ticks: { color: '#9ca3af' },
                        grid: { color: '#374151' }
                    }
                },
                plugins: {
                    legend: {
                        labels: {
                            color: '#d1d5db'
                        }
                    }
                }
            }
        });
    }
});
