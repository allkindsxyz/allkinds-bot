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
        .group-item { padding: 15px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; cursor: pointer; transition: background-color 0.2s; }
        .group-item:hover { background-color: #f8f9fa; }
        .group-item:last-child { border-bottom: none; }
        .group-name { font-weight: 600; color: #007AFF; }
        .group-stats { color: #666; font-size: 0.9em; }
        .refresh-btn { background: #007AFF; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; margin-left: 10px; }
        .refresh-btn:hover { background: #0056b3; }
        .loading { text-align: center; padding: 20px; color: #666; }
        .error { text-align: center; padding: 20px; color: #FF3B30; background: #FFE5E5; border-radius: 8px; margin: 10px 0; }
        .debug { background: #f0f0f0; padding: 10px; border-radius: 8px; margin: 10px 0; font-family: monospace; font-size: 0.8em; }
        .back-btn { background: #666; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; margin-right: 10px; }
        .back-btn:hover { background: #555; }
        .group-details { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .detail-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }
        .detail-row:last-child { border-bottom: none; }
        .detail-label { font-weight: 600; }
        .detail-value { color: #007AFF; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Allkinds Bot Analytics</h1>
            <p>Real-time analytics for your Telegram bot platform</p>
            <div>
                <button class="back-btn" id="backBtn" onclick="showOverview()" style="display: none;">← Back to Overview</button>
                <button class="refresh-btn" onclick="loadData()">🔄 Refresh</button>
                <button class="refresh-btn" onclick="testAPI()" style="background: #FF9500;">🧪 Test API</button>
            </div>
        </div>
        
        <div class="loading" id="loading">Loading analytics data...</div>
        <div class="error" id="error" style="display: none;"></div>
        <div class="debug" id="debug" style="display: none;"></div>
        
        <!-- Overview Section -->
        <div id="overviewSection">
            <div class="stats-grid" id="statsGrid" style="display: none;">
                <!-- Stats will be loaded here -->
            </div>
            
            <div class="chart-container" id="chartContainer" style="display: none;">
                <h3>Activity Overview</h3>
                <canvas id="activityChart" width="400" height="200"></canvas>
            </div>
            
            <div class="groups-list" id="groupsContainer" style="display: none;">
                <h3>Groups (click to view details)</h3>
                <div id="groupsList">
                    <!-- Groups will be loaded here -->
                </div>
            </div>
        </div>
        
        <!-- Group Details Section -->
        <div id="groupDetailsSection" style="display: none;">
            <div class="group-details" id="groupDetailsContainer">
                <!-- Group details will be loaded here -->
            </div>
        </div>
    </div>
    
    <script>
        let activityChart;
        let currentGroupId = null;
        let globalData = null;
        let groupsData = null;
        
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
        
        function showOverview() {
            currentGroupId = null;
            document.getElementById('overviewSection').style.display = 'block';
            document.getElementById('groupDetailsSection').style.display = 'none';
            document.getElementById('backBtn').style.display = 'none';
            
            if (globalData && groupsData) {
                updateStats(globalData);
                updateChart(globalData);
                updateGroups(groupsData);
                
                document.getElementById('loading').style.display = 'none';
                document.getElementById('statsGrid').style.display = 'grid';
                document.getElementById('chartContainer').style.display = 'block';
                document.getElementById('groupsContainer').style.display = 'block';
            }
        }
        
        async function showGroupDetails(groupId) {
            currentGroupId = groupId;
            hideError();
            document.getElementById('loading').innerHTML = `Loading group ${groupId} details...`;
            document.getElementById('loading').style.display = 'block';
            document.getElementById('overviewSection').style.display = 'none';
            document.getElementById('groupDetailsSection').style.display = 'block';
            document.getElementById('backBtn').style.display = 'inline-block';
            
            try {
                const response = await fetch(`/analytics/${groupId}/stats`);
                console.log(`Group ${groupId} response status:`, response.status);
                
                if (!response.ok) {
                    throw new Error(`Group stats API returned ${response.status}: ${response.statusText}`);
                }
                
                const groupStats = await response.json();
                console.log(`Group ${groupId} stats:`, groupStats);
                
                updateGroupDetails(groupStats);
                document.getElementById('loading').style.display = 'none';
                
            } catch (error) {
                console.error(`Error loading group ${groupId} details:`, error);
                showError(`Failed to load group ${groupId} details`, {
                    error: error.message,
                    groupId: groupId,
                    timestamp: new Date().toISOString()
                });
            }
        }
        
        function updateGroupDetails(groupStats) {
            const container = document.getElementById('groupDetailsContainer');
            container.innerHTML = `
                <h2>📊 ${groupStats.name}</h2>
                <p style="color: #666; margin-bottom: 20px;">${groupStats.description}</p>
                
                <div class="detail-row">
                    <span class="detail-label">👥 Total Members</span>
                    <span class="detail-value">${groupStats.member_count}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">👑 Creator</span>
                    <span class="detail-value">${groupStats.creator_name}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">📅 Created</span>
                    <span class="detail-value">${new Date(groupStats.created_at).toLocaleDateString()}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">❓ Total Questions</span>
                    <span class="detail-value">${groupStats.total_questions}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">💬 Total Answers</span>
                    <span class="detail-value">${groupStats.total_answers}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">⚡ Active Today</span>
                    <span class="detail-value">${groupStats.active_users_today}</span>
                </div>
                                 <div class="detail-row">
                     <span class="detail-label">📅 Active This Week</span>
                     <span class="detail-value">${groupStats.active_users_week}</span>
                 </div>
                 <div class="detail-row">
                     <span class="detail-label">📊 Avg Answers per User</span>
                     <span class="detail-value">${groupStats.avg_answers_per_user}</span>
                 </div>
                 <div class="detail-row">
                     <span class="detail-label">📊 Avg Questions per User</span>
                     <span class="detail-value">${groupStats.avg_questions_per_user}</span>
                 </div>
             `;
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
            
            if (currentGroupId) {
                // Reload group details if we're viewing a specific group
                showGroupDetails(currentGroupId);
                return;
            }
            
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
                
                globalData = await globalResponse.json();
                console.log('Global stats:', globalData);
                
                // Load groups
                console.log('Fetching groups...');
                const groupsResponse = await fetch('/analytics/');
                console.log('Groups response status:', groupsResponse.status);
                
                if (!groupsResponse.ok) {
                    throw new Error(`Groups API returned ${groupsResponse.status}: ${groupsResponse.statusText}`);
                }
                
                groupsData = await groupsResponse.json();
                console.log('Groups:', groupsData);
                
                updateStats(globalData);
                updateChart(globalData);
                updateGroups(groupsData);
                
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
                <div class="group-item" onclick="showGroupDetails(${group.id})">
                    <div>
                        <div class="group-name">${group.name} →</div>
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