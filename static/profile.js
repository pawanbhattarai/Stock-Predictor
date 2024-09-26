// Show the profile modal

document.addEventListener('DOMContentLoaded', function () {
    // Selecting all necessary elements
    const stockSelect = document.getElementById('stockSymbol');  // Correctly referenced stock input
    const portfolioList = document.getElementById('myprotfolio');
    const deleteStockSelect = document.getElementById('deleteStockSelect');
    const savePortfolioBtn = document.getElementById('savePortfolioBtn');
    const deleteStockButton = document.getElementById('deleteStockButton');
    const homelink = document.getElementById('homelink');   
    const myinfo = document.getElementById('myinfo');

    // Debugging Log
    console.log("Page loaded. JavaScript is running."); // Corrected typo
    
    // Home link click event
    if (homelink) {
        homelink.addEventListener('click', function (event) {
            event.preventDefault();
            console.log("Home link clicked, redirecting to /dashboard");
            window.location.href = "/dashboard";
        });
    }

    // // Check if stockSelect exists before populating dropdown
    // if (stockSelect) {
    //     // Populate stock dropdowns
    //     stockList.forEach(stock => {
    //         const option = document.createElement('option');
    //         option.value = stock;
    //         option.textContent = stock;
    //         stockSelect.appendChild(option);

    //         // Similarly, for deleteStockSelect if it exists
    //         if (deleteStockSelect) {
    //             const deleteOption = document.createElement('option');
    //             deleteOption.value = stock;
    //             deleteOption.textContent = stock;
    //             deleteStockSelect.appendChild(deleteOption);
    //         }
    //     });
    // } else {
    //     console.error('stockSelect not found in DOM');
    // }

    // Fetch and display portfolio stocks
    function loadPortfolio() {
        console.log("Fetching portfolio...");
        fetch('/get_portfolio')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                console.log("Portfolio fetched:", data);
                portfolioList.innerHTML = '';  // Clear existing portfolio items
                if (data.portfolio && data.portfolio.length > 0) {
                    data.portfolio.forEach(stock => {
                        const stockItem = document.createElement('div');
                        stockItem.className = 'portfolio-stock d-flex justify-content-between align-items-center';
    
                        // Create span for stock symbol
                        const stockSymbol = document.createElement('span');
                        stockSymbol.textContent = stock.symbol;
    
                        // Create span for stock quantity
                        const stockQuantity = document.createElement('span');
                        stockQuantity.textContent = stock.quantity;
                            // Create span for stock quantity
                        const purchasedPrice = document.createElement('span');
                        purchasedPrice.textContent = stock.price;
                        // Create delete button (X icon)
                        const deleteBtn = document.createElement('button');
                        deleteBtn.innerHTML = 'x';  // 'x' symbol
                        deleteBtn.className = 'btn btn-danger btn-sm';  // Optional Bootstrap styling for delete button
                        deleteBtn.style.height = '12px';
                        deleteBtn.style.width = '12px';  // Set height and width to the same size for a square button
                        deleteBtn.style.padding = '0';  // Remove padding to center the 'x'
                        deleteBtn.style.textAlign = 'center';  // Center the 'x' inside the button
                        deleteBtn.style.lineHeight = '10px';  // Vertically align the 'x'
                        


    
                        // Delete event handler
                        deleteBtn.addEventListener('click', function () {
                            if (confirm(`Are you sure you want to delete ${stock.symbol} from your portfolio?`)) {
                                deleteStock(stock.symbol, stockItem);  // Pass both symbol and the element to delete
                            }
                        });
    
                        stockItem.appendChild(stockSymbol);
                        stockItem.appendChild(stockQuantity);
                        stockItem.appendChild(purchasedPrice);  // Corrected this
                        stockItem.appendChild(deleteBtn);
                        

                        stockItem.appendChild(deleteBtn);
    
                        // Append stockItem to portfolioList
                        portfolioList.appendChild(stockItem);
                    });
                } else {
                    portfolioList.textContent = 'No stocks in portfolio.';
                }
            })
            .catch(error => console.error('Error fetching portfolio:', error));
    }
    
    // Function to handle stock deletion
    function deleteStock(symbol, stockItemElement) {
        fetch(`/delete_stock`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol: symbol })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log(`${symbol} deleted successfully.`);
                stockItemElement.remove();  // Remove the element from the DOM
            } else {
                console.error(`Failed to delete ${symbol}:`, data.error);
            }
        })
        .catch(error => console.error('Error deleting stock:', error));
    }
    
    
// Add stock to portfolio
if (savePortfolioBtn) {
    savePortfolioBtn.addEventListener('click', function (e) {
        e.preventDefault();
        const selectedStock = stockSelect ? stockSelect.value : null;
        const purchasedQuantity = document.getElementById('purchasedQuantity').value;
        const purchasedPrice = document.getElementById('purchasedprice').value;

        
        if (!selectedStock) {
            console.error('No stock selected!');
            return;
        }

        if (!purchasedQuantity || purchasedQuantity <= 0) {
            purchasedQuantity=0;
        }
        if (!purchasedPrice || purchasedPrice <= 0) {
            purchasedPrice=0;
        }

        console.log("Save button clicked. Selected stock:", selectedStock, "Quantity:", purchasedQuantity);

        fetch('/save_portfolio', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol: selectedStock, quantity: purchasedQuantity,price: purchasedPrice })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('Stock added successfully');
                loadPortfolio();  // Reload portfolio after adding the stock
            } else {
                console.error('Error adding stock:', data.error);
            }
        })
        .catch(error => console.error('Error adding stock:', error));
    });
} else {
    console.error("Save button not found in DOM.");
}

loadPortfolio(); // Initial load


    // Profile Modal Section
    function showProfileSection() {
        const profileModal = document.getElementById('profileModal');
        profileModal.style.display = 'block';

        // Fetch user details from the server
        fetch('/get_user_details', {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Populate the form with user data
                document.getElementById('name').value = data.name;
                document.getElementById('email').value = data.email;
                document.getElementById('password').value = data.password;

                // Store original values for comparison
                originalValues = {
                    name: data.name,
                    email: data.email,
                    password: data.password
                };

                // Initially hide the update button
                document.getElementById('updateButton').style.display = 'none';
            } else {
                alert('Failed to load user details: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while fetching user details.');
        });
    }

    // Close the profile modal
    function closeModal() {
        const profileModal = document.getElementById('profileModal');
        profileModal.style.display = 'none';
    }

    // Handle form submission
    document.getElementById('profileForm').addEventListener('submit', function(event) {
        event.preventDefault(); // Prevent form from submitting in the traditional way

        // Gather form data
        const formData = new FormData();

        // Get field values
        const name = document.getElementById('name').value;
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;

        // Append non-password fields to FormData
        formData.append('name', name);
        formData.append('email', email);

        // Only append password if it has been changed (i.e., not empty)
        if (password) {
            formData.append('password', password);
        }

        // Send an AJAX request to the server to update the user profile
        fetch('/update_profile', {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Profile updated successfully!');
                closeModal();  // Close modal after successful update
            } else {
                alert('Failed to update profile: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while updating the profile.');
        });
    });

    // Check if any form field has changed
    let originalValues = {}; 

    function checkChanges() {
        const name = document.getElementById('name').value;
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;

        // Compare current values with the original ones
        if (name !== originalValues.name || email !== originalValues.email || password !== originalValues.password) {
            // If any field has changed, show the Update button
            document.getElementById('updateButton').style.display = 'inline';
        } else {
            // If no changes, hide the Update button
            document.getElementById('updateButton').style.display = 'none';
        }
    }

    // Attach a click event listener to the profile link
    if (myinfo) {
        myinfo.addEventListener('click', function (event) {
            event.preventDefault();
            showProfileSection();
        });
    }

    // Attach change event listeners to form fields to detect changes
    document.getElementById('name').addEventListener('input', checkChanges);
    document.getElementById('email').addEventListener('input', checkChanges);
    document.getElementById('password').addEventListener('input', checkChanges);

    // Close the modal if clicked outside of it
    window.onclick = function(event) {
        if (event.target === document.getElementById('profileModal')) {
            closeModal();
        }
    }
});
