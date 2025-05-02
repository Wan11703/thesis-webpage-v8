// search bar

const searchWrapper = document.querySelector(".search-bar");
const inputBox = searchWrapper.querySelector("input");
const drug_list = searchWrapper.querySelector(".drug-list");

inputBox.onkeyup = (e) => {
    let userData = e.target.value;
    let emptyArray = [];
    if (userData) {
        emptyArray = auto_complete.filter((data) => {
            return data.toLocaleLowerCase().startsWith(userData.toLocaleLowerCase());
        });
        emptyArray = emptyArray.map((data) => {
            return data = `<li>${data}</li>`;
        });
        searchWrapper.classList.add("active");
        showDrugList(emptyArray);

        let allList = drug_list.querySelectorAll("li");
        for (let i = 0; i < allList.length; i++) {
            allList[i].setAttribute("onclick", "select(this)");
        }
    }
    else {
        searchWrapper.classList.remove("active");
    }
}

function select(element) {
    let selectedUserData = element.textContent;
    inputBox.value = selectedUserData;
    searchWrapper.classList.remove("active");
}

function showDrugList(list) {
    let listData;
    if (!list.length) {
        userValue = inputBox.value;
        listData = `<li>${userValue}</li>`;
    }
    else {
        listData = list.join('');
    }

    drug_list.innerHTML = listData;
}

// modal

const open = document.getElementById("open");
const modal_container = document.getElementById("modal_container");
const close = document.getElementById("close");
const modalTitle = document.querySelector("#modal-title");

const tabActive = document.querySelector(".tabs");
const loaderActive = document.querySelector(".loader");

let loading;


// modal


const drug_information = document.querySelector("#drug_information");
const interactions = document.querySelector("#interactions");
const indications = document.querySelector("#indications");
const side_effects = document.querySelector("#side_effects");
const price = document.querySelector("#price");




open.addEventListener('click', () => {
    const drugName = inputBox.value; // Get the search query from the input box
    modalTitle.textContent = "You searched for: " + inputBox.value;
    modal_container.classList.add('show');
    

    // Reset progress bar and start animation
    count = 0;
    per = 0;
    progress.style.width = "0px"; // Reset progress bar width
    loading = setInterval(animate, 150); // Start the animation

    // Send the drug name to the backend
    fetch('http://localhost:5000/get-drug-info', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ drug_name: drugName }), // Send the drug name as JSON
    })
    .then(response => response.json())
    .then(data => {
        // Update modal content with the response from the backend
        if (data.error) {
            drug_information.textContent = "";
            interactions.textContent = "";
            indications.textContent = "";
            side_effects.textContent = "";
            price.textContent = "";
        } else {
            drug_information.textContent = data.drug_information || "No details available.";
            interactions.textContent = data.interaction || "No interactions available.";
            indications.textContent = data.indication || "No indications available.";
            side_effects.textContent = data.side_effects || "No side effects available.";
            price.textContent = data.price || "No side effects available.";
        }
    })
    .catch(error => {
        console.error('Error:', error);
        drug_information.textContent = "Error fetching drug information.";
    });
});

close.addEventListener('click', () => {
    modal_container.classList.remove('show');

    // Stop and reset the animation
    clearInterval(loading); // Stop the interval
    count = 0;
    per = 0;
    progress.style.width = "0px"; // Reset progress bar width

    loaderActive.classList.add("active");
    tabActive.classList.remove("active");
});

// progress bar

var progress = document.querySelector(".progress");
var text = document.querySelector(".text");

var count = 0; // Start at 0%
var per = 0;   // Start at 0px

// var loading = setInterval(animate, 50);

function animate() {
  if ((count == 100) & (per == 600)) {
    text.classList.remove("text-blink");
    loaderActive.classList.remove("active");
    tabActive.classList.add("active");
  } else {
    text.classList.add("text-blink");
    per = per + 6;
    count = count + 1;
    progress.style.width = per + "px";
  }
}