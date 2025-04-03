// Global variables
let isLoggedIn = false;
let currentUser = null;
let userRole = null;

// API configuration
const API_BASE_URL = 'http://localhost:8000'; // FastAPI backend address

// Utility functions
function showMessage(message, isError = false) {
    const toast = document.createElement('div');
    toast.className = `toast ${isError ? 'toast-error' : 'toast-success'}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function validateForm(formData, rules) {
    for (const [field, rule] of Object.entries(rules)) {
        if (rule.required && !formData[field]) {
            throw new Error(`${field} is required`);
        }
        if (rule.minLength && formData[field].length < rule.minLength) {
            throw new Error(`${field} must be at least ${rule.minLength} characters`);
        }
    }
}

// Show/hide forms
function showLoginForm() {
    document.getElementById('loginForm').style.display = 'block';
    document.getElementById('registerForm').style.display = 'none';
    // Clear registration form
    document.getElementById('regUsername').value = '';
    document.getElementById('regPassword').value = '';
}

function showRegisterForm() {
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('registerForm').style.display = 'block';
    // Clear login form
    document.getElementById('loginUsername').value = '';
    document.getElementById('loginPassword').value = '';
}

// User registration
async function register(event) {
    event.preventDefault();
    const username = document.getElementById('regUsername').value;
    const password = document.getElementById('regPassword').value;

    try {
        validateForm(
            { username, password },
            {
                username: { required: true, minLength: 3 },
                password: { required: true, minLength: 6 }
            }
        );

        const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username,
                password,
                role: 'customer'
            })
        });

        if (response.ok) {
            showMessage('Registration successful!');
            showLoginForm();
        } else {
            const error = await response.json();
            showMessage(error.detail, true);
        }
    } catch (error) {
        showMessage(error.message, true);
    }
}

// User login
async function login(event) {
    event.preventDefault();
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;

    try {
        console.log('尝试登录...');
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                username,
                password
            }),
            credentials: 'include'
        });

        console.log('登录响应状态:', response.status);
        console.log('登录响应头:', Object.fromEntries(response.headers.entries()));
        
        const data = await response.json();
        console.log('登录响应数据:', data);

        if (!response.ok) {
            throw new Error(data.detail || '登录失败');
        }

        // 更新全局状态
        currentUser = {
            id: data.id,
            username: data.username,
            role: data.role
        };
        isLoggedIn = true;
        userRole = data.role;

        console.log('登录成功，用户信息:', currentUser);

        // 等待一小段时间让会话建立
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // 验证会话是否正确设置
        try {
            console.log('验证会话状态...');
            const sessionCheckResponse = await fetch(`${API_BASE_URL}/auth/status`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                },
                credentials: 'include'
            });

            if (!sessionCheckResponse.ok) {
                throw new Error('会话验证失败');
            }

            const sessionData = await sessionCheckResponse.json();
            console.log('会话验证成功:', sessionData);

            // 更新UI并加载数据
            updateUIAfterLogin();
            showMessage('登录成功！');
        } catch (sessionError) {
            console.error('会话验证失败:', sessionError);
            // 尝试重新登录
            isLoggedIn = false;
            currentUser = null;
            showMessage('登录失败：会话无效，请重试', true);
            return;
        }
    } catch (error) {
        console.error('登录失败:', error);
        showMessage(error.message || '登录失败', true);
    }
}

// User logout
async function logout() {
    try {
        await fetch(`${API_BASE_URL}/auth/logout`, {
            method: 'POST'
        });
        isLoggedIn = false;
        currentUser = null;
        userRole = null;
        updateUI();
        showMessage('Logged out successfully');
    } catch (error) {
        showMessage(error.message, true);
    }
}

// Update UI display
function updateUI() {
    const loginBtn = document.getElementById('loginBtn');
    const registerBtn = document.getElementById('registerBtn');
    const logoutBtn = document.getElementById('logoutBtn');
    const usernameSpan = document.getElementById('username');
    const myRecords = document.getElementById('myRecords');
    const adminSection = document.getElementById('adminSection');

    if (isLoggedIn && currentUser) {
        loginBtn.style.display = 'none';
        registerBtn.style.display = 'none';
        logoutBtn.style.display = 'block';
        usernameSpan.textContent = `welcome, ${currentUser.username}`;
        myRecords.style.display = 'block';
        
        if (currentUser.role === 'admin') {
            adminSection.style.display = 'block';
        } else {
            adminSection.style.display = 'none';
        }
    } else {
        loginBtn.style.display = 'block';
        registerBtn.style.display = 'block';
        logoutBtn.style.display = 'none';
        usernameSpan.textContent = '';
        myRecords.style.display = 'none';
        adminSection.style.display = 'none';
    }
}

// Load parking lots
async function loadParkingLots() {
    const parkingLotsList = document.getElementById('parkingLotsList');
    parkingLotsList.innerHTML = '<p class="loading">Loading...</p>';

    try {
        const searchLocation = document.getElementById('searchLocation').value;
        const url = new URL('/parking/lots', API_BASE_URL);
        if (searchLocation) {
            url.searchParams.append('location', searchLocation);
        }

        const response = await fetch(url.toString(), {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const parkingLots = await response.json();
        parkingLotsList.innerHTML = '';

        if (parkingLots.length === 0) {
            parkingLotsList.innerHTML = '<p class="no-data">No parking lots available</p>';
            return;
        }

        parkingLots.forEach(lot => {
            const card = document.createElement('div');
            card.className = 'parking-lot-card';
            card.innerHTML = `
                <h3>${lot.name || 'Unnamed Parking Lot'}</h3>
                <div class="parking-lot-info">
                    <p>Location: ${lot.location || 'Unknown'}</p>
                    <p>Description: ${lot.description || 'No description'}</p>
                    <p>Capacity: ${lot.capacity || 0}</p>
                    <p>Rate: $${lot.fee_rate || 0}/hour</p>
                    <p class="${lot.availability ? 'status-available' : 'status-full'}">
                        Status: ${lot.availability ? 'Available' : 'Full'}
                    </p>
                    ${isLoggedIn && lot.availability ? 
                        `<button onclick="checkIn(${lot.id})" class="btn-primary">Park Here</button>` : ''}
                    ${isLoggedIn && userRole === 'admin' ? 
                        `<button onclick="editParkingLot(${lot.id})" class="btn-secondary">Edit</button>` : ''}
                </div>
            `;
            parkingLotsList.appendChild(card);
        });
    } catch (error) {
        console.error('Failed to load parking lots:', error);
        parkingLotsList.innerHTML = '<p class="error-message">Failed to load parking lots</p>';
        showMessage(error.message, true);
    }
}

// Search parking lots
function searchParkingLots() {
    loadParkingLots();
}

// Load my records
async function loadMyRecords() {
    if (!isLoggedIn || !currentUser) {
        console.log('Not logged in');
        const recordsList = document.getElementById('recordsList');
        recordsList.innerHTML = '<p class="no-data">Login first</p>';
        return;
    }

    const recordsList = document.getElementById('recordsList');
    recordsList.innerHTML = '<p class="loading">Loading records...</p>';

    try {
        console.log('loading records...');
        console.log('current user status:', { isLoggedIn, currentUser });

        // 先检查登录状态
        const statusResponse = await fetch(`${API_BASE_URL}/auth/status`, {
            credentials: 'include',
            headers: {
                'Accept': 'application/json'
            }
        });

        if (!statusResponse.ok) {
            console.log('会话已过期，执行登出');
            isLoggedIn = false;
            currentUser = null;
            updateUI();
            recordsList.innerHTML = '<p class="error-message">Session expired, please login again</p>';
            showMessage('Session expired, please login again', true);
            return;
        }

        // 获取停车记录
        const response = await fetch(`${API_BASE_URL}/customer/my-records`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            },
            credentials: 'include'
        });

        console.log('records response status:', response.status);
        
        const responseText = await response.text();
        console.log('records original response:', responseText);
        
        let data;
        try {
            data = JSON.parse(responseText);
        } catch (e) {
            console.error('reading records failed:', e);
            throw new Error('server response format error');
        }

        if (!response.ok) {
            throw new Error(data.detail || 'loading records failed');
        }

        if (!Array.isArray(data)) {
            console.error('response data is not an array:', data);
            throw new Error('server returned data format error');
        }

        recordsList.innerHTML = '';

        if (data.length === 0) {
            recordsList.innerHTML = '<p class="no-data">No records</p>';
            return;
        }

        // 状态映射表
        const statusMap = {
            'PARKED': 'parked',
            'PAID': 'paid',
            'COMPLETED': 'completed',
            'parked': 'parked',
            'paid': 'paid',
            'completed': 'completed'
        };

        data.forEach(record => {
            const card = document.createElement('div');
            card.className = 'record-card';
            
            // 确保所有必需的字段都存在
            const safeRecord = {
                id: record.id || '未知',
                car_number: record.car_number || '未知',
                parking_lot_id: record.parking_lot_id || '未知',
                entry_time: record.entry_time ? new Date(record.entry_time).toLocaleString() : '未知',
                status: record.status || 'UNKNOWN',
                exit_time: record.exit_time ? new Date(record.exit_time).toLocaleString() : null,
                amount: record.amount || 0
            };

            // 获取状态显示文本
            const statusText = statusMap[safeRecord.status] || '未知状态';
            // 判断是否为停车中状态
            const isParked = safeRecord.status.toLowerCase() === 'parked';

            card.innerHTML = `
                <h3>record #${safeRecord.id}</h3>
                <div class="record-info">
                    <p>car number: ${safeRecord.car_number}</p>
                    <p>parking lot id: ${safeRecord.parking_lot_id}</p>
                    <p>entry time: ${safeRecord.entry_time}</p>
                    <p>status: ${statusText}</p>
                    ${safeRecord.exit_time ? `<p>exit time: ${safeRecord.exit_time}</p>` : ''}
                    ${safeRecord.amount > 0 ? `<p>amount: ¥${safeRecord.amount.toFixed(2)}</p>` : ''}
                    ${isParked ? `<button onclick="checkOut(${safeRecord.id})" class="btn-primary">end parking</button>` : ''}
                </div>
            `;
            recordsList.appendChild(card);
        });
    } catch (error) {
        console.error('loading records failed:', error);
        recordsList.innerHTML = '<p class="error-message">loading records failed</p>';
        showMessage(error.message || 'loading records failed', true);
    }
}

// Check in (park)
async function checkIn(parkingLotId) {
    if (!isLoggedIn) {
        showMessage('请先登录', true);
        return;
    }

    const carNumber = prompt('please input car number:');
    if (!carNumber) {
        showMessage('please input a valid car number', true);
        return;
    }

    try {
        console.log('attempting to create a parking record...', {
            car_number: carNumber,
            parking_lot_id: parkingLotId,
            isLoggedIn,
            currentUser
        });

        const response = await fetch(`${API_BASE_URL}/customer/records`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                car_number: carNumber,
                parking_lot_id: parkingLotId
                // 不发送status字段，让后端使用默认值
            }),
            credentials: 'include'
        });

        console.log('parking request response status:', response.status);
        
        let data;
        const responseText = await response.text();
        console.log('parking request original response:', responseText);
        
        try {
            data = JSON.parse(responseText);
        } catch (e) {
            console.error('parsing response JSON failed:', e);
            throw new Error('server response format error');
        }

        if (!response.ok) {
            if (response.status === 401) {
                isLoggedIn = false;
                currentUser = null;
                updateUI();
                throw new Error('session expired, please login again');
            } else if (response.status === 400) {
                throw new Error(data.detail || 'request parameter error');
            } else if (response.status === 500) {
                throw new Error('server internal error, please try again later');
            }
            throw new Error(data.detail || 'parking failed');
        }

        showMessage('parking successful!');
        await loadParkingLots();
        await loadMyRecords();
    } catch (error) {
        console.error('parking failed:', error);
        showMessage(error.message || 'parking failed', true);
    }
}

// Check out
async function checkOut(recordId) {
    try {
        console.log('attempting to end a parking record:', recordId);
        
        // 先检查登录状态
        if (!isLoggedIn || !currentUser) {
            console.log('user not logged in, cannot end parking');
            showMessage('please login first', true);
            return;
        }
        
        console.log('current user:', currentUser);
        
        const response = await fetch(`${API_BASE_URL}/customer/records/${recordId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                status: 'COMPLETED'  // 使用大写的状态值
            }),
            credentials: 'include'
        });

        console.log('ending parking request response status:', response.status);
        
        let data;
        const responseText = await response.text();
        console.log('ending parking request original response:', responseText);
        
        try {
            data = JSON.parse(responseText);
        } catch (e) {
            console.error('parsing response JSON failed:', e);
            throw new Error('server response format error');
        }

        if (!response.ok) {
            if (response.status === 401) {
                isLoggedIn = false;
                currentUser = null;
                updateUI();
                throw new Error('session expired, please login again');
            } else if (response.status === 403) {
                throw new Error('no permission to modify this record');
            } else if (response.status === 404) {
                throw new Error('record not found');
            } else if (response.status === 500) {
                throw new Error('server internal error, please try again later');
            }
            throw new Error(data.detail || 'ending parking failed');
        }

        showMessage('parking ended successfully!');
        await loadParkingLots();
        await loadMyRecords();
    } catch (error) {
        console.error('ending parking failed:', error);
        showMessage(error.message || 'ending parking failed', true);
    }
}

// Admin: Edit parking lot
async function editParkingLot(lotId) {
    if (!isLoggedIn || currentUser.role !== 'admin') {
        showMessage('no admin permission', true);
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/parking/lots/${lotId}`, {
            credentials: 'include',
            headers: {
                'Accept': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error('failed to get parking lot information');
        }

        const lot = await response.json();
        const newData = {
            name: prompt('input parking lot name:', lot.name),
            location: prompt('input location:', lot.location),
            description: prompt('input description:', lot.description),
            capacity: parseInt(prompt('input capacity:', lot.capacity)),
            fee_rate: parseFloat(prompt('input fee rate:', lot.fee_rate))
        };

        if (Object.values(newData).some(value => value === null)) {
            return;
        }

        const updateResponse = await fetch(`${API_BASE_URL}/admin/parkinglots/${lotId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(newData),
            credentials: 'include'
        });

        const data = await updateResponse.json();
        if (!updateResponse.ok) {
            throw new Error(data.detail || 'failed to update parking lot information');
        }

        showMessage('parking lot information updated successfully!');
        loadParkingLots();
    } catch (error) {
        showMessage(error.message || 'operation failed', true);
    }
}

// Load all records (admin only)
async function loadAllRecords() {
    if (!isLoggedIn || currentUser.role !== 'admin') {
        console.log('non-admin user, do not load all records');
        return;
    }

    const allRecordsList = document.getElementById('allRecordsList');
    allRecordsList.innerHTML = '<p class="loading">loading all records...</p>';

    try {
        const response = await fetch(`${API_BASE_URL}/admin/records`, {
            credentials: 'include',
            headers: {
                'Accept': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error('failed to load records');
        }

        const records = await response.json();
        allRecordsList.innerHTML = '';

        if (!Array.isArray(records) || records.length === 0) {
            allRecordsList.innerHTML = '<p class="no-data">no parking records</p>';
            return;
        }

        records.forEach(record => {
            const card = document.createElement('div');
            card.className = 'record-card';
            card.innerHTML = `
                <h3>parking record #${record.id}</h3>
                <div class="record-info">
                    <p>user id: ${record.user_id}</p>
                    <p>car number: ${record.car_number}</p>
                    <p>parking lot id: ${record.parking_lot_id}</p>
                    <p>entry time: ${new Date(record.entry_time).toLocaleString()}</p>
                    <p>status: ${record.status === 'PARKED' ? 'parked' : 'completed'}</p>
                    ${record.exit_time ? `<p>exit time: ${new Date(record.exit_time).toLocaleString()}</p>` : ''}
                    ${record.amount ? `<p>amount: ¥${record.amount}</p>` : ''}
                </div>
            `;
            allRecordsList.appendChild(card);
        });
    } catch (error) {
        console.error('failed to load all records:', error);
        allRecordsList.innerHTML = '<p class="error-message">failed to load records</p>';
        showMessage(error.message || 'failed to load records', true);
    }
}

// Update UI after login
function updateUIAfterLogin() {
    const loginBtn = document.getElementById('loginBtn');
    const registerBtn = document.getElementById('registerBtn');
    const logoutBtn = document.getElementById('logoutBtn');
    const usernameSpan = document.getElementById('username');
    const myRecords = document.getElementById('myRecords');
    const adminSection = document.getElementById('adminSection');
    const loginForm = document.getElementById('loginForm');

    loginBtn.style.display = 'none';
    registerBtn.style.display = 'none';
    logoutBtn.style.display = 'block';
    loginForm.style.display = 'none';
    usernameSpan.textContent = `welcome, ${currentUser.username}`;
    myRecords.style.display = 'block';

    if (currentUser.role === 'admin') {
        adminSection.style.display = 'block';
        loadAllRecords();
    } else {
        adminSection.style.display = 'none';
    }

    // 加载数据
    loadParkingLots();
    loadMyRecords();
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    loadParkingLots();
    // Check if user is already logged in
    fetch(`${API_BASE_URL}/auth/status`, {
        credentials: 'include',
        headers: {
            'Accept': 'application/json'
        }
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('not logged in');
            }
            return response.json();
        })
        .then(data => {
            // 更新全局状态
            currentUser = {
                id: data.id,
                username: data.username,
                role: data.role
            };
            isLoggedIn = true;
            userRole = data.role;

            console.log('logged in, user info:', currentUser);
            updateUIAfterLogin();
        })
        .catch(error => {
            console.log('not logged in or session expired:', error);
            // 确保用户状态为未登录
            currentUser = null;
            isLoggedIn = false;
            userRole = null;
            updateUI();
        });
}); 