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
        .error { text-align: center; padding: 20px; color: #FF3B30; background: #FFE5E5; border-radius: 8px; margin: 10px 0; }
        .debug { background: #f0f0f0; padding: 10px; border-radius: 8px; margin: 10px 0; font-family: monospace; font-size: 0.8em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Allkinds Bot Analytics</h1>
            <p>Real-time analytics for your Telegram bot platform</p>
            <button class="refresh-btn" onclick="loadData()">🔄 Refresh</button>
            <button class="refresh-btn" onclick="testAPI()" style="background: #FF9500;">🧪 Test API</button>
        </div>
        
        <div class="loading" id="loading">Loading analytics data...</div>
        <div class="error" id="error" style="display: none;"></div>
        <div class="debug" id="debug" style="display: none;"></div>
        
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
        
        function showError(message, details = null) {
            const errorDiv = document.getElementById('error');
            const debugDiv = document.getElementById('debug');
            
            errorDiv.innerHTML = `❌ ${message}`;
            errorDiv.style.display = 'block';
            
            if (details) {
                debugDiv.innerHTML = `Debug info: ${JSON.stringify(details, null, 2)}`;
                debugDiv.style.display = 'block';
            }
            
            document.getElementById('loading').style.display = 'none';
        }
        
        function hideError() {
            document.getElementById('error').style.display = 'none';
            document.getElementById('debug').style.display = 'none';
        }
        
        async function testAPI() {
            hideError();
            document.getElementById('loading').innerHTML = 'Testing API...';
            document.getElementById('loading').style.display = 'block';
            
            try {
                const response = await fetch('/test');
                const data = await response.json();
                
                if (response.ok) {
                    showError('✅ Test API works! Now trying real endpoints...', data);
                    setTimeout(loadData, 2000);
                } else {
                    showError('Test API failed', {status: response.status, data});
                }
            } catch (error) {
                showError('Test API error', {error: error.message});
            }
        }
        
        async function loadData() {
            hideError();
            document.getElementById('loading').innerHTML = 'Loading analytics data...';
            document.getElementById('loading').style.display = 'block';
            document.getElementById('statsGrid').style.display = 'none';
            document.getElementById('chartContainer').style.display = 'none';
            document.getElementById('groupsContainer').style.display = 'none';
            
            try {
                // Load global stats
                console.log('Fetching global stats...');
                const globalResponse = await fetch('/analytics/global');
                console.log('Global response status:', globalResponse.status);
                
                if (!globalResponse.ok) {
                    throw new Error(`Global stats API returned ${globalResponse.status}: ${globalResponse.statusText}`);
                }
                
                const globalStats = await globalResponse.json();
                console.log('Global stats:', globalStats);
                
                // Load groups
                console.log('Fetching groups...');
                const groupsResponse = await fetch('/analytics/');
                console.log('Groups response status:', groupsResponse.status);
                
                if (!groupsResponse.ok) {
                    throw new Error(`Groups API returned ${groupsResponse.status}: ${groupsResponse.statusText}`);
                }
                
                const groups = await groupsResponse.json();
                console.log('Groups:', groups);
                
                updateStats(globalStats);
                updateChart(globalStats);
                updateGroups(groups);
                
                document.getElementById('loading').style.display = 'none';
                document.getElementById('statsGrid').style.display = 'grid';
                document.getElementById('chartContainer').style.display = 'block';
                document.getElementById('groupsContainer').style.display = 'block';
                
            } catch (error) {
                console.error('Error loading data:', error);
                showError('Failed to load analytics data', {
                    error: error.message,
                    timestamp: new Date().toISOString()
                });
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
        
        // Auto-refresh every 60 seconds (increased from 30 to reduce load during debugging)
        setInterval(loadData, 60000);
    </script>
</body>
</html>
""" 