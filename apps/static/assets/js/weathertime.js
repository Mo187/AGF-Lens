// Function to update the current time
function updateTime() {
    const now = new Date();
    let hours = now.getHours();
    const minutes = now.getMinutes().toString().padStart(2, '0');
    const ampm = hours >= 12 ? 'PM' : 'AM';

    hours = hours % 12;
    hours = hours ? hours : 12; // the hour '0' should be '12'
    const timeString = `${hours}:${minutes} ${ampm}`;
    document.getElementById('current-time').textContent = timeString;
}
function updateWeather() {
    const apiKey = 'af42a60c841402c42fe9cf7fe632cf83';
    const city = 'Nairobi'; // Replace with your city
    const url = `https://api.openweathermap.org/data/2.5/weather?q=${city}&units=metric&appid=${apiKey}`;

    fetch(url)
        .then(response => response.json())
        .then(data => {
            console.log('Weather Data:', data); // For debugging
            const temperature = Math.round(data.main.temp); // Round the temperature
            const weatherDescription = data.weather[0].description;
            const iconCode = data.weather[0].icon; // Get the icon code
            const iconUrl = `https://openweathermap.org/img/wn/${iconCode}@2x.png`; // Construct the icon URL

            const weatherString = `<img src="${iconUrl}" alt="${weatherDescription}"> ${temperature}°C | ${weatherDescription}`;
            document.getElementById('current-weather').innerHTML = weatherString;
        })
        .catch(error => console.log('Error fetching weather data:', error));
}


// Update time and weather every minute
setInterval(updateTime, 60000);
setInterval(updateWeather, 60000);

// Initial call to display time and weather on page load
updateTime();
updateWeather();



