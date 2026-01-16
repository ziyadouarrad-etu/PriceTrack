from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from .models import SearchHistory
from .forms import UserRegisterForm
from .utils import get_results_safe
from asgiref.sync import sync_to_async
from django.contrib.auth import login, get_user
# --- Session Helpers (Same as before) ---
@sync_to_async
def get_cached_data(request, query):
    if request.session.get('last_query') == query:
        return request.session.get('cached_results')
    return None

@sync_to_async
def set_cached_data(request, query, results):
    request.session['last_query'] = query
    request.session['cached_results'] = results
    request.session.modified = True

# --- The Views ---

# Async Search View
async def search_view(request):
# 1. Safely fetch the user data in a sync-to-async wrapper
    user = await sync_to_async(get_user)(request)
    
    # 2. Check authentication and get the username as a simple string
    is_auth = await sync_to_async(lambda: user.is_authenticated)()
    
    if not is_auth:
        return redirect('login')
    
    # Pre-fetch the username so the template doesn't have to
    user_name = await sync_to_async(lambda: user.username)()
    query = request.GET.get('q')
    sort_order = request.GET.get('sort', 'asc')
    # Get the list of selected sites from the checkboxes
    selected_sites = request.GET.getlist('sites') 
    
    results = []

    if query:
        # 1. Get data (Session or Scraper)
        results = await get_cached_data(request, query)
        if results is None:
            results = await get_results_safe(query)
            await set_cached_data(request, query, results)
        
        # 2. SAVE TO DATABASE
            # We use sync_to_async because saving to DB is a synchronous action
            await sync_to_async(SearchHistory.objects.create)(
                user=user,
                query=query,
                results_data=results
            )

        # 3. FILTER by Site
        # If the user selected specific sites, filter the list
        if selected_sites:
            results = [item for item in results if item.get('source') in selected_sites]

        # 4. SORT by Price
        is_reverse = (sort_order == 'desc')
        results.sort(key=lambda x: x.get('price', 0), reverse=is_reverse)

    return render(request, 'App/results.html', {
        'results': results,
        'query': query,
        'sort_order': sort_order,
        'selected_sites': selected_sites, # Send this back to keep checkboxes checked
        'user_name': user_name,           # Send username for display
    })

# Landing View
def landing_view(request):
    if request.user.is_authenticated:
        return redirect('search') # Send them to the app if already logged in
    return render(request, 'App/landing.html')

# Standard Sync Registration
def register_view(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('search') # Redirect to the Async page
    else:
        form = UserRegisterForm()
    return render(request, 'registration/register.html', {'form': form})

# Standard Sync Login
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('search')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

# History View
@login_required
def history_view(request):
    # Fetch all searches for the logged-in user, newest first
    history_items = SearchHistory.objects.filter(user=request.user).order_by('-timestamp')
    
    return render(request, 'App/history.html', {
        'history': history_items
    })

@login_required
def snapshot_view(request, pk):
    entry = get_object_or_404(SearchHistory, pk=pk, user=request.user)
    
    # Extract stored data
    results = entry.results_data
    query = entry.query
    timestamp = entry.timestamp

    # Get Filter/Sort params from the URL
    sort_order = request.GET.get('sort', 'asc')
    selected_sites = request.GET.getlist('sites')
    original_sites = list(set(item.get('source') for item in results))
    # 1. FILTER: By Site
    if selected_sites:
        results = [item for item in results if item.get('source') in selected_sites]
    else:
        # Default to all sites if none selected
        selected_sites = original_sites

    # 2. SORT: By Price
    is_reverse = (sort_order == 'desc')
    # Use float/int conversion to ensure mathematical sorting
    results.sort(key=lambda x: float(x.get('price', 0)), reverse=is_reverse)

    return render(request, 'App/snapshot.html', {
        'results': results,
        'query': query,
        'timestamp': timestamp,
        'original_sites': original_sites,
        'selected_sites': selected_sites,
        'sort_order': sort_order
    })