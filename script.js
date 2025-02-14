document.addEventListener("DOMContentLoaded", function() {
    fetchTransactions();
});

function fetchTransactions() {
    fetch("http://127.0.0.1:5000/get_transactions")  // Replace with your API endpoint
        .then(response => response.json())
        .then(data => {
            displayTransactions(data);
        })
        .catch(error => console.error("Error fetching transactions:", error));
}

function displayTransactions(transactions) {
    const tableBody = document.getElementById("transactionTable");
    tableBody.innerHTML = "";

    transactions.forEach(transaction => {
        let row = `<tr>
            <td>${new Date(transaction.transaction_date).toLocaleString()}</td>
            <td>${transaction.merchant}</td>
            <td>${transaction.category}</td>
            <td>₹${transaction.amount.toFixed(2)}</td>
            <td>${transaction.transaction_type}</td>
        </tr>`;
        tableBody.innerHTML += row;
    });
}

function filterTransactions() {
    const searchQuery = document.getElementById("search").value.toLowerCase();
    const categoryFilter = document.getElementById("categoryFilter").value;

    fetch("http://127.0.0.1:5000/get_transactions")
        .then(response => response.json())
        .then(data => {
            let filteredTransactions = data.filter(transaction => {
                return (
                    (categoryFilter === "All" || transaction.category === categoryFilter) &&
                    (transaction.merchant.toLowerCase().includes(searchQuery) ||
                     transaction.amount.toString().includes(searchQuery))
                );
            });

            displayTransactions(filteredTransactions);
        })
        .catch(error => console.error("Error filtering transactions:", error));
}
