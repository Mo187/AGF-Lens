const themeSwitch = document.getElementById("theme-switch"); //our switch element
const themeIndicator = document.getElementById("theme-indicator"); //our theme icon
const page = document.body; //our document body

//To avoid any confusion, all variables are placed inside arrays.
const themeStates = ["light", "dark"];
const indicators = ["icon-moon", "icon-sun"];

//This is a helper function to set the theme.
function setTheme(theme) {
    localStorage.setItem("theme", themeStates[theme]);
}

//This is a helper function to set the icon.
function setIndicator(theme) {
    themeIndicator.classList.remove(indicators[0]);
    themeIndicator.classList.remove(indicators[1]);
    themeIndicator.classList.add(indicators[theme]);
}

//This is a helper function to set the page theme class.
function setPage(theme) {
    if (theme === 1) {
        page.classList.add("dark");
    } else {
        page.classList.remove("dark");
    }
}

// Ensure the correct theme is set after page load
const currentTheme = localStorage.getItem("theme");

if (currentTheme === "dark") {
    setIndicator(1);
    setPage(1);
    themeSwitch.checked = false;
} else if (currentTheme === "light") {
    setTheme(1); // Force dark mode if somehow it's in light mode
    setIndicator(1);
    setPage(1);
    themeSwitch.checked = false;
}

// Disable theme switching
themeSwitch.addEventListener('change', function () {
    themeSwitch.checked = false; // Ensure the switch stays unchecked
});
