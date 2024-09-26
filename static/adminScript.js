document.addEventListener("DOMContentLoaded", function () {
    fetch('/get_all_users')
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          const userTableBody = document.getElementById('userTableBody');
          userTableBody.innerHTML = '';

          // Populate users
          data.users.forEach(user => {
            const row = document.createElement('tr');
            row.innerHTML = `
              <td>${user.username}</td>
              <td>${user.email}</td>
              <td>
                <button onclick="viewPredictions(${user.id})">View Predictions</button>
                <button onclick="deleteUser(${user.id})">Delete</button>
              </td>
            `;
            userTableBody.appendChild(row);
          });
        } else {
          alert('Failed to fetch user data: ' + data.error);
        }
      })
      .catch(error => console.error('Error:', error));
  });

  function viewPredictions(userId) {
    $.ajax({
      url: `/get_user_predictions/${userId}`,
      type: 'GET',
      success: function (response) {
        const savedPredictionsContainer = $('.saved-predictions');
        savedPredictionsContainer.empty(); // Clear any existing saved predictions

        if (response.success) {
          // Populate saved predictions
          if (response.saved_predictions && response.saved_predictions.length > 0) {
            response.saved_predictions.forEach(function (prediction) {
              savedPredictionsContainer.append(`
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

            // Attach click event to each saved prediction
            $('.saved-prediction').on('click', function (e) {
              e.preventDefault();
              const predictionId = $(this).data('id');
              loadPredictionDetails(predictionId);
            });
          } else {
            savedPredictionsContainer.html('<p>No Saved Data.</p>');
          }
        } else {
          alert('No predictions found for this user.');
        }
      },
      error: function () {
        alert('Error loading saved predictions.');
      }
    });
  }

  // Load prediction details for a specific prediction when clicked
  function loadPredictionDetails(predictionId) {
    $.ajax({
      url: `/saved_prediction/${predictionId}`,
      type: 'GET',
      success: function (response) {
        const predictionTableBody = $('#predictionTable');
        predictionTableBody.empty(); // Clear any existing predictions
        if (response.success) {
          // Populate prediction table with details
          response.prediction.forEach(function (dayPrediction) {
            const row = `
            <tr>
              <td>${dayPrediction.day}</td>
              <td>${dayPrediction.predicted_close}</td>
            </tr>
          `;
            predictionTableBody.append(row);
          });
        } else {
          alert('No prediction data found.');
        }
      },
      error: function () {
        alert('Error loading prediction details.');
      }
    });
  }

  // Delete user functionality
  function deleteUser(userId) {
    fetch(`/delete_user/${userId}`, { method: 'DELETE' })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          alert('User deleted successfully');
          location.reload(); // Reload the page to update the table
        } else {
          alert('Failed to delete user: ' + data.error);
        }
      });
  }
  function deletePrediction(predictionId) {
    if (confirm('Are you sure you want to delete this prediction?')) {
      $.ajax({
        url: `/delete_prediction/${predictionId}`,
        type: 'DELETE',
        success: function (response) {
          if (response.success) {
            alert('Prediction deleted successfully.');
            loadSavedPredictions({ userId });  // Refresh the list after deletion
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
  $('#updateStock').on('click', function (event) {
    event.preventDefault(); // Prevent default button behavior
    $.ajax({
        url: '/scrape_stocks', // Flask route to fetch the stocks
        type: 'GET',
        success: function (response) {
            if (response.success) {
                alert("Successfully updated/added stocks");
            } else {
                alert("Failed to update/add stocks");
            }
        },
        error: function () {
            alert('Error occurred while updating stocks.');
        }
    });
});


$.ajax({
  url: '/all_stocks', // Flask route to fetch the stocks
  type: 'GET',
  success: function (response) {
      const listedStocksTableBody = $('#stockTableBody');  // Select the table body with id "stockTableBody"
      listedStocksTableBody.empty(); // Clear any existing rows

      if (response.success) {
          // Loop through each stock and append a row to the table
          response.listed_stocks.forEach(function (stock) {
              const stockRow = `
                  <tr>
                    <td>${stock.Symbol}</td>
                    <td>${stock.Name}</td>
                  </tr>
              `;
              listedStocksTableBody.append(stockRow);  // Append each stock to the table body
          });
      } else {
          listedStocksTableBody.append('<tr><td colspan="2">No listed stocks found.</td></tr>');
      }
  },
  error: function () {
      alert('Error loading listed stocks.');
  }

});

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