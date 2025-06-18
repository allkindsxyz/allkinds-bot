"""HTML dashboard template for analytics"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Allkinds Bot Analytics</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f7; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .stat-number { font-size: 2.5em; font-weight: bold; color: #007AFF; margin-bottom: 5px; }
        .stat-label { color: #666; font-size: 0.9em; }
        .chart-container { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .groups-list { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .group-item { padding: 15px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
        .group-item:last-child { border-bottom: none; }
        .group-name { font-weight: 600; }
        .group-stats { color: #666; font-size: 0.9em; }
        .refresh-btn { background: #007AFF; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; margin-left: 10px; }
        .refresh-btn:hover { background: #0056b3; }
        .loading { text-align: center; padding: 20px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Allkinds Bot Analytics</h1>
            <p>Real-time analytics for your Telegram bot platform</p>
            <button class="refresh-btn" onclick="loadData()">🔄 Refresh</button>
        </div>
        
        <div class="loading" id="loading">Loading analytics data...</div>
        
        <div class="stats-grid" id="statsGrid" style="display: none;">
            <!-- Stats will be loaded here -->
        </div>
        
        <div class="chart-container" id="chartContainer" style="display: none;">
            <h3>Activity Overview</h3>
            <canvas id="activityChart" width="400" height="200"></canvas>
        </div>
        
        <div class="groups-list" id="groupsContainer" style="display: none;">
            <h3>Groups</h3>
            <div id="groupsList">
                <!-- Groups will be loaded here -->
            </div>
        </div>
    </div>
    
    <script>
        let activityChart;
        
        async function loadData() {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('statsGrid').style.display = 'none';
            document.getElementById('chartContainer').style.display = 'none';
            document.getElementById('groupsContainer').style.display = 'none';
            
            try {
                // Load global stats
                const globalResponse = await fetch('/analytics/global');
                const globalStats = await globalResponse.json();
                
                // Load groups
                const groupsResponse = await fetch('/analytics/');
                const groups = await groupsResponse.json();
                
                updateStats(globalStats);
                updateChart(globalStats);
                updateGroups(groups);
                
                document.getElementById('loading').style.display = 'none';
                document.getElementById('statsGrid').style.display = 'grid';
                document.getElementById('chartContainer').style.display = 'block';
                document.getElementById('groupsContainer').style.display = 'block';
                
            } catch (error) {
                console.error('Error loading data:', error);
                document.getElementById('loading').innerHTML = '❌ Error loading data. Please try again.';
            }
        }
        
        function updateStats(stats) {
            const statsGrid = document.getElementById('statsGrid');
            statsGrid.innerHTML = `
                <div class="stat-card">
                    <div class="stat-number">${stats.total_users}</div>
                    <div class="stat-label">👥 Total Users</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${stats.total_groups}</div>
                    <div class="stat-label">🏘️ Total Groups</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${stats.total_questions}</div>
                    <div class="stat-label">❓ Questions Asked</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${stats.total_answers}</div>
                    <div class="stat-label">💬 Answers Given</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${stats.active_users_week}</div>
                    <div class="stat-label">📅 Active This Week</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${stats.active_users_today}</div>
                    <div class="stat-label">⚡ Active Today</div>
                </div>
            `;
        }
        
        function updateChart(stats) {
            const ctx = document.getElementById('activityChart').getContext('2d');
            
            if (activityChart) {
                activityChart.destroy();
            }
            
            activityChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Questions', 'Answers'],
                    datasets: [{
                        data: [stats.total_questions, stats.total_answers],
                        backgroundColor: ['#007AFF', '#34C759'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        }
        
        function updateGroups(groups) {
            const groupsList = document.getElementById('groupsList');
            
            if (groups.length === 0) {
                groupsList.innerHTML = '<p>No groups found</p>';
                return;
            }
            
            groupsList.innerHTML = groups.map(group => `
                <div class="group-item">
                    <div>
                        <div class="group-name">${group.name}</div>
                        <div class="group-stats">👤 ${group.member_count} members • 👑 ${group.creator_name}</div>
                        <div class="group-stats" style="margin-top: 5px;">${group.description}</div>
                    </div>
                    <div class="group-stats">
                        ${new Date(group.created_at).toLocaleDateString()}
                    </div>
                </div>
            `).join('');
        }
        
        // Load data on page load
        loadData();
        
        // Auto-refresh every 30 seconds
        setInterval(loadData, 30000);
    </script>
</body>
</html>
""" 