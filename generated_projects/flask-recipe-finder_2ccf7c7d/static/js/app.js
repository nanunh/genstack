// DOM Elements
const searchForm = document.getElementById('search-form');
const ingredientsInput = document.getElementById('ingredients');
const searchResults = document.getElementById('search-results');
const recipeDetailsContent = document.getElementById('recipe-details-content');
const favoritesContent = document.getElementById('favorites-content');
const noFavorites = document.getElementById('no-favorites');

// Pages
const pageHome = document.getElementById('page-home');
const pageRecipeDetails = document.getElementById('page-recipe-details');
const pageFavorites = document.getElementById('page-favorites');
const pageAdmin = document.getElementById('page-admin');

// Navigation
const navHome = document.getElementById('nav-home');
const navFavorites = document.getElementById('nav-favorites');
const navAdmin = document.getElementById('nav-admin');
const btnBackToResults = document.getElementById('btn-back-to-results');
const btnBrowseRecipes = document.getElementById('btn-browse-recipes');

// Auth elements
const authButtons = document.getElementById('auth-buttons');
const userInfo = document.getElementById('user-info');
const usernameSpan = document.getElementById('username');
const btnLogin = document.getElementById('btn-login');
const btnRegister = document.getElementById('btn-register');
const btnLogout = document.getElementById('btn-logout');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const loginError = document.getElementById('login-error');
const registerError = document.getElementById('register-error');

// Admin elements
const usersTableBody = document.getElementById('users-table-body');
const userCount = document.getElementById('user-count');
const searchCount = document.getElementById('search-count');
const viewCount = document.getElementById('view-count');
const favoriteCount = document.getElementById('favorite-count');
const popularRecipesBody = document.getElementById('popular-recipes-body');

// Bootstrap modals
const loginModal = new bootstrap.Modal(document.getElementById('loginModal'));
const registerModal = new bootstrap.Modal(document.getElementById('registerModal'));

// State
let currentUser = null;
let lastSearchResults = [];
let currentRecipe = null;

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    // Check if user is logged in
    checkAuthStatus();
    
    // Navigation
    navHome.addEventListener('click', showHomePage);
    navFavorites.addEventListener('click', showFavoritesPage);
    navAdmin.addEventListener('click', showAdminPage);
    btnBackToResults.addEventListener('click', showHomePage);
    btnBrowseRecipes.addEventListener('click', showHomePage);
    
    // Forms
    searchForm.addEventListener('submit', handleSearch);
    loginForm.addEventListener('submit', handleLogin);
    registerForm.addEventListener('submit', handleRegister);
    
    // Auth buttons
    btnLogin.addEventListener('click', () => loginModal.show());
    btnRegister.addEventListener('click', () => registerModal.show());
    btnLogout.addEventListener('click', handleLogout);
});

// Page Navigation Functions
function showHomePage(e) {
    if (e) e.preventDefault();
    pageHome.style.display = 'block';
    pageRecipeDetails.style.display = 'none';
    pageFavorites.style.display = 'none';
    pageAdmin.style.display = 'none';
    
    navHome.classList.add('active');
    navFavorites.classList.remove('active');
    navAdmin.classList.remove('active');
}

function showRecipeDetailsPage() {
    pageHome.style.display = 'none';
    pageRecipeDetails.style.display = 'block';
    pageFavorites.style.display = 'none';
    pageAdmin.style.display = 'none';
    
    navHome.classList.add('active');
    navFavorites.classList.remove('active');
    navAdmin.classList.remove('active');
}

function showFavoritesPage(e) {
    if (e) e.preventDefault();
    
    if (!currentUser) {
        loginModal.show();
        return;
    }
    
    pageHome.style.display = 'none';
    pageRecipeDetails.style.display = 'none';
    pageFavorites.style.display = 'block';
    pageAdmin.style.display = 'none';
    
    navHome.classList.remove('active');
    navFavorites.classList.add('active');
    navAdmin.classList.remove('active');
    
    loadFavorites();
}

function showAdminPage(e) {
    if (e) e.preventDefault();
    
    if (!currentUser || !currentUser.is_admin) {
        showHomePage();
        return;
    }
    
    pageHome.style.display = 'none';
    pageRecipeDetails.style.display = 'none';
    pageFavorites.style.display = 'none';
    pageAdmin.style.display = 'block';
    
    navHome.classList.remove('active');
    navFavorites.classList.remove('active');
    navAdmin.classList.add('active');
    
    loadAdminData();
}

// API Functions
async function searchRecipes(ingredients) {
    try {
        const response = await fetch(`/api/search?ingredients=${encodeURIComponent(ingredients)}`);
        if (!response.ok) throw new Error('Search failed');
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error searching recipes:', error);
        return [];
    }
}

async function getRecipeDetails(recipeId) {
    try {
        const response = await fetch(`/api/recipe/${recipeId}`);
        if (!response.ok) throw new Error('Failed to get recipe details');
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error getting recipe details:', error);
        return null;
    }
}

async function getFavorites() {
    try {
        const response = await fetch('/api/favorites');
        if (!response.ok) throw new Error('Failed to get favorites');
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error getting favorites:', error);
        return [];
    }
}

async function addFavorite(recipe) {
    try {
        const response = await fetch('/api/favorites', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                recipe_id: recipe.id,
                recipe_title: recipe.title,
                recipe_image: recipe.image
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to add favorite');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error adding favorite:', error);
        throw error;
    }
}

async function removeFavorite(recipeId) {
    try {
        const response = await fetch('/api/favorites', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                recipe_id: recipeId
            })
        });
        
        if (!response.ok) throw new Error('Failed to remove favorite');
        return await response.json();
    } catch (error) {
        console.error('Error removing favorite:', error);
        throw error;
    }
}

async function login(username, password) {
    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Login failed');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error logging in:', error);
        throw error;
    }
}

async function register(username, email, password) {
    try {
        const response = await fetch('/api/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, email, password })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Registration failed');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error registering:', error);
        throw error;
    }
}

async function logout() {
    try {
        const response = await fetch('/api/logout', {
            method: 'POST'
        });
        
        if (!response.ok) throw new Error('Logout failed');
        return await response.json();
    } catch (error) {
        console.error('Error logging out:', error);
        throw error;
    }
}

async function checkAuthStatus() {
    try {
        const response = await fetch('/api/user');
        
        if (response.ok) {
            const userData = await response.json();
            updateUserState(userData);
        } else {
            updateUserState(null);
        }
    } catch (error) {
        console.error('Error checking auth status:', error);
        updateUserState(null);
    }
}

async function getAdminUsers() {
    try {
        const response = await fetch('/api/admin/users');
        if (!response.ok) throw new Error('Failed to get users');
        
        return await response.json();
    } catch (error) {
        console.error('Error getting users:', error);
        return [];
    }
}

async function getAdminAnalytics() {
    try {
        const response = await fetch('/api/admin/analytics');
        if (!response.ok) throw new Error('Failed to get analytics');
        
        return await response.json();
    } catch (error) {
        console.error('Error getting analytics:', error);
        return { user_count: 0, activity_counts: {}, popular_recipes: [] };
    }
}

// Event Handlers
async function handleSearch(e) {
    e.preventDefault();
    const ingredients = ingredientsInput.value.trim();
    
    if (!ingredients) {
        alert('Please enter at least one ingredient');
        return;
    }
    
    searchResults.innerHTML = '<div class="col-12 text-center"><div class="spinner-border" role="status"></div></div>';
    
    const results = await searchRecipes(ingredients);
    lastSearchResults = results;
    
    displaySearchResults(results);
}

async function handleRecipeClick(recipeId) {
    recipeDetailsContent.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div></div>';
    showRecipeDetailsPage();
    
    const recipe = await getRecipeDetails(recipeId);
    if (recipe) {
        currentRecipe = recipe;
        displayRecipeDetails(recipe);
    } else {
        recipeDetailsContent.innerHTML = '<div class="alert alert-danger">Failed to load recipe details</div>';
    }
}

async function handleFavoriteClick(recipe, button) {
    if (!currentUser) {
        loginModal.show();
        return;
    }
    
    try {
        if (button.classList.contains('favorited')) {
            await removeFavorite(recipe.id);
            button.innerHTML = '<i class="far fa-heart"></i>';
            button.classList.remove('favorited');
        } else {
            await addFavorite(recipe);
            button.innerHTML = '<i class="fas fa-heart"></i>';
            button.classList.add('favorited');
        }
    } catch (error) {
        alert(error.message);
    }
}

async function handleLogin(e) {
    e.preventDefault();
    
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    
    loginError.style.display = 'none';
    
    try {
        const data = await login(username, password);
        updateUserState(data.user);
        loginModal.hide();
        loginForm.reset();
    } catch (error) {
        loginError.textContent = error.message;
        loginError.style.display = 'block';
    }
}

async function handleRegister(e) {
    e.preventDefault();
    
    const username = document.getElementById('register-username').value;
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;
    const confirmPassword = document.getElementById('register-confirm-password').value;
    
    registerError.style.display = 'none';
    
    if (password !== confirmPassword) {
        registerError.textContent = 'Passwords do not match';
        registerError.style.display = 'block';
        return;
    }
    
    try {
        await register(username, email, password);
        registerModal.hide();
        registerForm.reset();
        loginModal.show();
    } catch (error) {
        registerError.textContent = error.message;
        registerError.style.display = 'block';
    }
}

async function handleLogout() {
    try {
        await logout();
        updateUserState(null);
        showHomePage();
    } catch (error) {
        alert(error.message);
    }
}

// UI Update Functions
function updateUserState(user) {
    currentUser = user;
    
    if (user) {
        authButtons.style.display = 'none';
        userInfo.style.display = 'flex';
        usernameSpan.textContent = user.username;
        
        // Show admin nav if user is admin
        const adminElements = document.querySelectorAll('.admin-only');
        adminElements.forEach(el => {
            el.style.display = user.is_admin ? 'block' : 'none';
        });
    } else {
        authButtons.style.display = 'flex';
        userInfo.style.display = 'none';
        usernameSpan.textContent = '';
        
        // Hide admin elements
        const adminElements = document.querySelectorAll('.admin-only');
        adminElements.forEach(el => {
            el.style.display = 'none';
        });
    }
}

function displaySearchResults(recipes) {
    if (!recipes || recipes.length === 0) {
        searchResults.innerHTML = '<div class="col-12"><div class="alert alert-info">No recipes found. Try different ingredients.</div></div>';
        return;
    }
    
    searchResults.innerHTML = '';
    
    recipes.forEach(recipe => {
        const col = document.createElement('div');
        col.className = 'col';
        
        const card = document.createElement('div');
        card.className = 'card recipe-card';
        
        const img = document.createElement('img');
        img.src = recipe.image;
        img.className = 'card-img-top';
        img.alt = recipe.title;
        
        const cardBody = document.createElement('div');
        cardBody.className = 'card-body';
        
        const title = document.createElement('h5');
        title.className = 'card-title';
        title.textContent = recipe.title;
        
        const usedIngredients = document.createElement('p');
        usedIngredients.className = 'used-ingredients';
        usedIngredients.innerHTML = `<i class="fas fa-check-circle"></i> ${recipe.usedIngredientCount} ingredients used`;
        
        const missingIngredients = document.createElement('p');
        missingIngredients.className = 'missing-ingredients';
        missingIngredients.innerHTML = `<i class="fas fa-times-circle"></i> ${recipe.missedIngredientCount} ingredients missing`;
        
        const viewButton = document.createElement('button');
        viewButton.className = 'btn btn-primary mt-2';
        viewButton.textContent = 'View Recipe';
        viewButton.addEventListener('click', () => handleRecipeClick(recipe.id));
        
        cardBody.appendChild(title);
        cardBody.appendChild(usedIngredients);
        cardBody.appendChild(missingIngredients);
        cardBody.appendChild(viewButton);
        
        card.appendChild(img);
        card.appendChild(cardBody);
        col.appendChild(card);
        
        searchResults.appendChild(col);
    });
}

async function displayRecipeDetails(recipe) {
    // Check if recipe is in favorites
    let isFavorite = false;
    if (currentUser) {
        const favorites = await getFavorites();
        isFavorite = favorites.some(fav => fav.recipe_id === recipe.id);
    }
    
    const html = `
        <div class="recipe-header">
            <img src="${recipe.image}" alt="${recipe.title}">
            <button class="favorite-btn ${isFavorite ? 'favorited' : ''}" id="favorite-btn">
                <i class="${isFavorite ? 'fas' : 'far'} fa-heart"></i>
            </button>
            <div class="recipe-title-container">
                <h1 class="recipe-title">${recipe.title}</h1>
                <div class="recipe-meta">
                    <div class="recipe-meta-item">
                        <i class="fas fa-clock"></i>
                        <span>${recipe.readyInMinutes} minutes</span>
                    </div>
                    <div class="recipe-meta-item">
                        <i class="fas fa-utensils"></i>
                        <span>${recipe.servings} servings</span>
                    </div>
                    ${recipe.vegetarian ? `
                    <div class="recipe-meta-item">
                        <i class="fas fa-leaf"></i>
                        <span>Vegetarian</span>
                    </div>` : ''}
                    ${recipe.vegan ? `
                    <div class="recipe-meta-item">
                        <i class="fas fa-seedling"></i>
                        <span>Vegan</span>
                    </div>` : ''}
                    ${recipe.glutenFree ? `
                    <div class="recipe-meta-item">
                        <i class="fas fa-bread-slice"></i>
                        <span>Gluten Free</span>
                    </div>` : ''}
                    ${recipe.dairyFree ? `
                    <div class="recipe-meta-item">
                        <i class="fas fa-cheese"></i>
                        <span>Dairy Free</span>
                    </div>` : ''}
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-md-4">
                <div class="ingredients-list">
                    <h3>Ingredients</h3>
                    <ul>
                        ${recipe.extendedIngredients.map(ingredient => `
                            <li>${ingredient.original}</li>
                        `).join('')}
                    </ul>
                </div>
            </div>
            <div class="col-md-8">
                <div class="instructions">
                    <h3>Instructions</h3>
                    ${recipe.instructions ? `
                        <div>${recipe.instructions}</div>
                    ` : `
                        <ol>
                            ${recipe.analyzedInstructions[0]?.steps.map(step => `
                                <li>${step.step}</li>
                            `).join('') || '<li>No instructions available</li>'}
                        </ol>
                    `}
                </div>
            </div>
        </div>
    `;
    
    recipeDetailsContent.innerHTML = html;
    
    // Add event listener to favorite button
    const favoriteBtn = document.getElementById('favorite-btn');
    if (favoriteBtn) {
        favoriteBtn.addEventListener('click', () => handleFavoriteClick(recipe, favoriteBtn));
    }
}

async function loadFavorites() {
    favoritesContent.innerHTML = '<div class="col-12 text-center"><div class="spinner-border" role="status"></div></div>';
    
    const favorites = await getFavorites();
    
    if (favorites.length === 0) {
        favoritesContent.innerHTML = '';
        noFavorites.style.display = 'block';
        return;
    }
    
    noFavorites.style.display = 'none';
    favoritesContent.innerHTML = '';
    
    favorites.forEach(favorite => {
        const col = document.createElement('div');
        col.className = 'col';
        
        const card = document.createElement('div');
        card.className = 'card recipe-card';
        
        const img = document.createElement('img');
        img.src = favorite.recipe_image || 'https://via.placeholder.com/300x200?text=No+Image';
        img.className = 'card-img-top';
        img.alt = favorite.recipe_title;
        
        const cardBody = document.createElement('div');
        cardBody.className = 'card-body';
        
        const title = document.createElement('h5');
        title.className = 'card-title';
        title.textContent = favorite.recipe_title;
        
        const viewButton = document.createElement('button');
        viewButton.className = 'btn btn-primary mt-2';
        viewButton.textContent = 'View Recipe';
        viewButton.addEventListener('click', () => handleRecipeClick(favorite.recipe_id));
        
        const removeButton = document.createElement('button');
        removeButton.className = 'btn btn-outline-danger mt-2 ms-2';
        removeButton.textContent = 'Remove';
        removeButton.addEventListener('click', async () => {
            try {
                await removeFavorite(favorite.recipe_id);
                loadFavorites(); // Reload favorites
            } catch (error) {
                alert(error.message);
            }
        });
        
        cardBody.appendChild(title);
        cardBody.appendChild(viewButton);
        cardBody.appendChild(removeButton);
        
        card.appendChild(img);
        card.appendChild(cardBody);
        col.appendChild(card);
        
        favoritesContent.appendChild(col);
    });
}

async function loadAdminData() {
    // Load users
    const users = await getAdminUsers();
    usersTableBody.innerHTML = '';
    
    users.forEach(user => {
        const row = document.createElement('tr');
        
        row.innerHTML = `
            <td>${user.id}</td>
            <td>${user.username}</td>
            <td>${user.email}</td>
            <td>${user.is_admin ? 'Admin' : 'User'}</td>
            <td>${new Date(user.created_at).toLocaleDateString()}</td>
        `;
        
        usersTableBody.appendChild(row);
    });
    
    // Load analytics
    const analytics = await getAdminAnalytics();
    
    userCount.textContent = analytics.user_count;
    searchCount.textContent = analytics.activity_counts.search || 0;
    viewCount.textContent = analytics.activity_counts.view || 0;
    favoriteCount.textContent = analytics.activity_counts.favorite || 0;
    
    popularRecipesBody.innerHTML = '';
    
    analytics.popular_recipes.forEach(recipe => {
        const row = document.createElement('tr');
        
        row.innerHTML = `
            <td>${recipe.recipe_title}</td>
            <td>${recipe.favorite_count}</td>
        `;
        
        popularRecipesBody.appendChild(row);
    });
}

// Initialize the app
showHomePage();