$(document).ready(function () {
    // Hide spinner and save button initially
    $('.loading-spinner').hide();
    $('#savePredictionButton').hide();

    // Popup elements for login requirement
    const popup = $('<div>').addClass('popup-overlay').hide();
    const popupContent = $('<div>').addClass('popup-content');
    const title = $('<h4>').text('You’ve hit the limit');
    const message = $('<p>').text('You can only predict one stock without logging in. Please log in to access additional features and make more predictions.');
    const loginButton = $('<button>').attr('id', 'loginButton').text('Login');
    const cancelButton = $('<button>').attr('id', 'cancelButton').text('Cancel');
    const profileLink = document.getElementById('profileLink');
    if (profileLink) {
        profileLink.addEventListener('click', function (event) {
            event.preventDefault();
            window.location.href = "/redirect_to_profile";  // Redirect to the backend route
        });
    } else {
        console.error('profileLink element not found');
    }

    
    popupContent.append(title, message, loginButton, cancelButton);
    popup.append(popupContent);
    $('body').append(popup);

    // Popup display functions
    function showPopup() {
        popup.show();
    }

    function hidePopup() {
        popup.hide();
    }

    // Load saved predictions
    function loadSavedPredictions() {
        $.ajax({
            url: '/saved_predictions',
            type: 'GET',
            success: function (response) {
                $('.saved-predictions').empty();
                if (response.saved_predictions && response.saved_predictions.length > 0) {
                    response.saved_predictions.forEach(function (prediction) {
                        $('.saved-predictions').append(`
                        <div class="d-flex justify-content-between align-items-center">
                            <a href="#" class="saved-prediction" data-id="${prediction.p_id}">
                                ${prediction.symbol} - ${new Date(prediction.created_at).toLocaleDateString()}
                            </a>
                            <button class="btn btn-danger" onclick="deletePrediction(${prediction.p_id})" title="Delete" style="width: 15px; height: 15px; padding: 0; display: flex; align-items: center; justify-content: center;">
                                x
                            </button>

                        </div>
                        `);
                    });
                } else {
                    $('.saved-predictions').html('<p>No Saved Data.</p>');
                }
            },
            error: function () {
                $('.saved-predictions').html('<p>Error loading saved predictions.</p>');
            }
        });
    }

    loadSavedPredictions(); // Load saved predictions on page load

    // Handle click on saved prediction
    $(document).on('click', '.saved-prediction', function (e) {
        e.preventDefault();
        const p_id = $(this).data('id');

        
        $.ajax({
            url: `/saved_prediction/${p_id}`,
            type: 'GET',
            success: function (response) {
                $('#predictionTable').empty();
                const prediction = response.prediction;

                if (prediction) {
                    prediction.forEach(function (item) {
                        $('#predictionTable').append(`
                            <tr>
                            <td>${item.day}</td>
                            <td>${item.predicted_close}</td>

                            </tr>
                        `);
                    });
                    $('#savePredictionButton').hide(); // Hide Save button if the data is already saved
                    hidePreviousLTPColumn();
                } else {
                    $('#predictionTable').append('<tr><td colspan="2">No prediction details available.</td></tr>');
                }
            },
            error: function (xhr) {
                $('#predictionTable').empty();
                const error = xhr.responseJSON ? xhr.responseJSON.error : 'Unknown error';
                $('#predictionTable').append(`<tr><td colspan="2">Error: ${error}</td></tr>`);
            }
        });
    });
    function hidePreviousLTPColumn() {
        const previousLTPHeader = document.getElementById('previousLTPHeader');
        const previousLTPCells = document.querySelectorAll('td.previousLTP');
        
        previousLTPHeader.style.display = 'none';  // Hide header
        previousLTPCells.forEach(cell => {
          cell.style.display = 'none';  // Hide all cells in the column
        });
      }
      function showPreviousLTPColumn() {
        const previousLTPHeader = document.getElementById('previousLTPHeader');
        const previousLTPCells = document.querySelectorAll('td.previousLTP');
        
        previousLTPHeader.style.display = '';  // Show header
        previousLTPCells.forEach(cell => {
          cell.style.display = '';  // Show all cells in the column
        });
      }
    // Handle prediction requests
    $('#predict_3_days, #predict_7_days').on('click', function () {
        const days = $(this).attr('id') === 'predict_3_days' ? 3 : 7;
        submitPredictionRequest(days);
    });

    function submitPredictionRequest(days) {
        $('.loading-spinner').show();
        $('#savePredictionButton').hide();

        const stockSymbol = $('#stock_symbol').val().trim().toUpperCase(); // Convert symbol to uppercase

        if (!stockSymbol) {
            alert('Please enter a valid stock symbol.');
            $('.loading-spinner').hide();
            return;
        }

        const data = {
            symbol: stockSymbol,
            days: days
        };

        $.ajax({
            url: '/predict',
            type: 'POST',
            data: JSON.stringify(data),
            contentType: 'application/json',
            success: function (response) {
                $('.loading-spinner').hide();
                $('#predictionTable').empty();

                if (response.predictions && response.predictions.length > 0) {
                    response.predictions.forEach(function (row) {
                        $('#predictionTable').append(`
                            <tr><td>${row.day}</td><td>${row.predicted_close}</td><td>${row.historical_close}</td></tr>
                        `);
                    });
                    $('#savePredictionButton').show();
                    showPreviousLTPColumn();

                    // Display the graph below the table
                    displayPredictionGraph(response.predictions);
                } else {
                    $('#predictionTable').append('<tr><td colspan="2">No predictions available.</td></tr>');
                }
            },
            error: function (xhr) {
                $('.loading-spinner').hide();
                $('#predictionTable').empty();
                const error = xhr.responseJSON ? xhr.responseJSON.error : 'Unknown error';
                if (error === "logging required") {
                    showPopup(); // Show login popup if needed
                }
            }
        });
    }

    function displayPredictionGraph(data) {
        const ctx = document.getElementById('predictionGraph').getContext('2d');
    
        // Separate historical data and predicted data
        const historicalData = data.filter(item => item.historical_close !== null);
        const predictedData = data.filter(item => item.predicted_close !== null);
    
        // Reverse historical data so that Previous Day 1 is the most recent
        const reversedHistoricalData = historicalData.reverse();
    
        // Create custom labels for historical and predicted days
        const totalHistoricalDays = historicalData.length;

        const historicalLabels = reversedHistoricalData.map((item, index) => `Previous Day ${totalHistoricalDays - index}`);
        const predictedLabels = predictedData.map((item, index) => `Future Day ${index + 1}`);
    
        // Data arrays for historical and predicted prices
        const historicalPrices = reversedHistoricalData.map(item => item.historical_close);
        const predictedPrices = predictedData.map(item => item.predicted_close);
    
        // Combine historical and predicted prices into one array for a smooth connection
        const combinedPrices = [...historicalPrices, ...predictedPrices];
    
        // Combine labels for both historical and predicted days
        const combinedLabels = [...historicalLabels, ...predictedLabels];
    
        // Destroy existing chart instance before creating a new one
        if (window.predictionChart) {
            window.predictionChart.destroy();
        }
    
        // Create the chart with combined datasets for continuous connection
        window.predictionChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: combinedLabels,  // Combined labels for the x-axis
                datasets: [
                    {
                        label: 'Stock Prices',
                        data: combinedPrices,  // Combined prices for both historical and predicted data
                        borderColor: function(context) {
                            const index = context.dataIndex;
                            const totalHistoricalPoints = historicalPrices.length;
                            // Color logic: Blue for historical, Red for predicted
                            return index < totalHistoricalPoints ? 'blue' : 'red';
                        },
                        pointBackgroundColor: function(context) {
                            const index = context.dataIndex;
                            const totalHistoricalPoints = historicalPrices.length;
                            // Point color logic: Blue for historical, Red for predicted
                            return index < totalHistoricalPoints ? 'blue' : 'red';
                        },
                        fill: false,
                        borderWidth: 2,
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        callbacks: {
                            label: function (tooltipItem) {
                                return tooltipItem.dataset.label + ': ' + tooltipItem.raw.toFixed(2);
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Days'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Stock Price'
                        }
                    }
                }
            }
        });
    }
        
        
    
    
    // Handle saving predictions
    $('#savePredictionButton').on('click', function () {
        const stockSymbol = $('#stock_symbol').val().trim();

        if (!stockSymbol || $('#predictionTable tr').length === 0) {
            alert('No prediction data available to save.');
            return;
        }

        const prediction = [];
        $('#predictionTable tr').each(function () {
            const day = $(this).find('td:eq(0)').text();
            const predicted_close = $(this).find('td:eq(1)').text();
            if (day && predicted_close) {
                prediction.push({ day: day, predicted_close: predicted_close });
            }
        });

        if (prediction.length === 0) {
            alert('No valid prediction data found.');
            return;
        }

        $.ajax({
            url: '/save_prediction',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                symbol: stockSymbol,
                prediction: prediction
            }),
            success: function (response) {
                if (response.success) {
                    loadSavedPredictions(); // Reload saved predictions after saving
                    alert('Prediction saved successfully.');
                    $('#savePredictionButton').hide(); // Hide Save button after saving
                } else {
                    alert('Error saving prediction.');
                }
            },
            error: function () {
                alert('Error saving prediction.');
            }
        });
    });
    
    
    // Handle login button click in popup
    $('#loginButton').on('click', function () {
        window.location.href = '/login'; // Redirect to login page
    });

    // Handle cancel button click in popup
    $('#cancelButton').on('click', function () {
        hidePopup();
    });

    // Logout confirmation dialog
    $('#logoutLink').on('click', function (event) {
        event.preventDefault(); // Prevent default link behavior
        $('#confirmationDialog').show();
    });

    $('#confirmLogout').on('click', function () {
        window.location.href = '/logout'; // Redirect to logout route
    });

    $('#cancelLogout').on('click', function () {
        $('#confirmationDialog').hide();
    });

    // Login link redirection
    $('#loginLink').on('click', function (event) {
        event.preventDefault();
        window.location.href = '/login'; // Redirect to login page
    });

    // Register/Login form toggle logic
    const registerForm = $('#registerForm');
    const loginForm = $('#loginForm');
    const toggleLogin = $('#toggleLogin');
    const toggleRegister = $('#toggleRegister');

    // Function to switch to login form
    function switchToLoginForm() {
        registerForm.hide();
        loginForm.show();
    }

    // Function to switch to register form
    function switchToRegisterForm() {
        loginForm.hide();
        registerForm.show();
    }

    // Event listener for "Login?" link
    toggleLogin.on('click', function (event) {
        event.preventDefault();
        switchToLoginForm();
    });
    // Event listener for login form submission
    loginForm.on('submit', function (event) {
        event.preventDefault(); // Prevent the default form submission
    
        const loginUsername = $('#loginUsername').val().trim();
        const loginPassword = $('#loginPassword').val().trim();
    
        if (loginUsername === '' || loginPassword === '') {
            alert('Please fill in all fields.');
            return;
        }
    
        // Send the form data using fetch
        fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username: loginUsername, password: loginPassword })
        })
        .then(response => response.json())
        .then(data => {
            if (data.redirect_url) {
                // Redirect to the URL returned by the Flask backend
                window.location.href = data.redirect_url;
            } else if (data.error) {
                // Handle errors
                alert(data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred. Please try again.');
        });
    });
    

    // Event listener for "Register?" link
    toggleRegister.on('click', function (event) {
        event.preventDefault();
        switchToRegisterForm();
    });
    // Event listener for registration form submission
    registerForm.on('submit', function (event) {
        event.preventDefault(); // Prevent the default form submission

        const username = $('#username').val().trim();
        const password = $('#password').val().trim();
        const confirmPassword = $('#confirmPassword').val().trim();
        const email = $('#email').val().trim();

        // Check if any field is empty
        if (username === '' || password === '' || confirmPassword === '' || email === '') {
            alert('Please fill in all fields.');
            return;
        }

        // Check if username is at least 3 characters long
        if (username.length < 3) {
            alert('Username must be at least 3 characters long.');
            return;
        }

        // Check if password and confirmPassword match
        if (password !== confirmPassword) {
            alert('Passwords do not match.');
            return;
        }

        // Check if password contains at least one letter, one number, and one special character
        const passwordRegex = /^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;
        if (!passwordRegex.test(password)) {
            alert('Password must contain at least 8 characters, including at least one letter, one number, and one special character.');
            return;
        }

        // Check if email is valid using a basic regex
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            alert('Please enter a valid email address.');
            return;
        }

        // Send the form data using fetch
        fetch('/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password, email })
        })
            .then(response => {
                if (response.ok) {
                    return response.json(); // Assuming the server responds with JSON
                } else {
                    return response.text().then(text => {
                        throw new Error(text); // Throw an error with the response text
                    });
                }
            })
            .then(data => {
                alert("Sucessfully RegisterdAmazing! Your Account has been Created Successfully.")
                switchToLoginForm();
            })
            .catch(error => {
                console.error('Error:', error);
                // alert(An Error occurred: ${ error.message }); // Provide detailed error message
            });
    });

    
    // Close confirmation dialog if "Cancel" button is clicked
    $('#cancelLogout').on('click', function () {
        $('#confirmationDialog').hide();
    });

});
function loadPortfolio() {
    console.log("Fetching portfolio...");
    fetch('/all_stocks') // Fetch from the backend
        .then(response => response.json())
        .then(data => {
            console.log("Portfolio fetched:", data);
            
            const stockSelect = document.getElementById('stock_symbol');
            stockSelect.innerHTML = '';  // Clear existing options

            // Check if listed_stocks array is returned
            if (data.success && data.listed_stocks.length > 0) {
                data.listed_stocks.forEach(stock => {
                    const option = document.createElement('option');
                    option.value = stock.Symbol;  // Stock symbol
                    option.textContent = stock.Symbol;  // Display stock symbol
                    stockSelect.appendChild(option);
                });
            } else {
                const noStockOption = document.createElement('option');
                noStockOption.textContent = "No stocks available";
                noStockOption.disabled = true;
                stockSelect.appendChild(noStockOption);
            }
        })
        .catch(error => console.error('Error fetching portfolio:', error));
}


// Call loadPortfolio to populate dropdown on page load
document.addEventListener('DOMContentLoaded', loadPortfolio);

function deletePrediction(predictionId) {
    if (confirm('Are you sure you want to delete this prediction?')) {
        $.ajax({
            url: `/delete_prediction/${predictionId}`,
            type: 'DELETE',
            success: function (response) {
                if (response.success) {
                    alert('Prediction deleted successfully.');
                    location.reload();
                } else {
                    alert('Error deleting prediction: ' + response.error);
                }
            },
            error: function () {
                alert('Error deleting prediction.');
            }
        });
    }
}