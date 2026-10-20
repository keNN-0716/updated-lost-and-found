from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponseForbidden, JsonResponse, HttpResponse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .forms import CustomLoginForm, CustomSignupForm, LostItemForm, FoundItemForm, ClaimRequestForm
from .models import LostItem, FoundItem, ItemStatus, ClaimRequest
from .decorators import management_required
from .notifications import notify_express
from io import BytesIO
import qrcode

def is_management(user):
    """True if the user is staff or has the Management role."""
    return user.is_staff or getattr(user, 'role', None) == 'Management'


# ─────────────────────────────────────────────────────────────────
# Search
# ─────────────────────────────────────────────────────────────────
@login_required
def search_results(request):
    query = request.GET.get('q', '').strip()
    results = []
    if query:
        results = LostItem.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(location_lost__icontains=query)
        ).exclude(status=ItemStatus.RESOLVED).order_by('-created_at') # Excludes resolved items
        
    return render(request, 'search_results.html', {
        'results': results, 
        'query': query,
        'is_management': is_management(request.user) # Pass management status for buttons
    })


@login_required
def search_api(request):
    """
    JSON endpoint used by Express for live search.
    Express forwards the browser's session cookie, so @login_required works.
    """
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': {'lost': [], 'found': []}})

    lost = list(
        LostItem.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(location_lost__icontains=query)
        ).values('item_id', 'name', 'location_lost', 'status')[:5]
    )
    found = list(
        FoundItem.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(location_found__icontains=query)
        ).values('item_id', 'name', 'location_found', 'status')[:5]
    )
    return JsonResponse({'results': {'lost': lost, 'found': found}})


# ─────────────────────────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────────────────────────
def signup_view(request):
    if request.method == 'POST':
        form = CustomSignupForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = CustomSignupForm()
    return render(request, 'signup.html', {'form': form})


def login_view(request):
    error_message = None
    if request.method == 'POST':
        form = CustomLoginForm(request.POST)
        if form.is_valid():
            id_number = form.cleaned_data.get('id_number')
            password = form.cleaned_data.get('password')
            user = authenticate(request, id_number=id_number, password=password)
            if user is not None:
                login(request, user)
                return redirect('login_redirect')
            else:
                error_message = 'Invalid ID number or password.'
    else:
        form = CustomLoginForm()
    return render(request, 'login.html', {'form': form, 'error_message': error_message})


@login_required
def login_redirect_view(request):
    if is_management(request.user):
        return redirect('lost_and_found')
    return redirect('user_home_page')


def logout_view(request):
    if request.method == 'POST':
        logout(request)
    return redirect('login')


# ─────────────────────────────────────────────────────────────────
# Items
# ─────────────────────────────────────────────────────────────────
@login_required
def lost_items(request):
    is_manager = is_management(request.user)

    if request.method == 'POST':
        # ONLY management can report lost items
        if not is_manager:
            return HttpResponseForbidden("Only management can report lost items.")
            
        form = LostItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.reported_by = request.user
            item.save()
            notify_express('item_reported', {
                'type': 'lost', 'id': item.item_id, 'name': item.name, 'location': item.location_lost, 'status': item.status,
            })
            messages.success(request, f'"{item.name}" has been reported.')
            return redirect('lost_items')
    else:
        form = LostItemForm()

    lost_items_qs = LostItem.objects.exclude(status=ItemStatus.RESOLVED).order_by('-created_at')
    
    return render(request, 'lost_items.html', {
        'lost_items': lost_items_qs,
        'form': form,
        'is_management': is_manager,
    })
    
@login_required
@management_required
def lost_and_found(request):
    return render(request, 'lost_and_found.html')


@login_required
def found_items(request):
    if request.method == 'POST':
        form = FoundItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.reported_by = request.user
            item.save()
            notify_express('item_reported', {
                'type': 'found',
                'id': item.item_id,
                'name': item.name,
                'location': item.location_found,
                'status': item.status,
            })
            messages.success(request, f'"{item.name}" has been reported as found.')
            return redirect('found_items')
    else:
        form = FoundItemForm()

    found_items_qs = FoundItem.objects.all().order_by('-created_at')
    return render(request, 'found_items.html', {
        'found_items': found_items_qs,
        'form': form,
        'is_management': is_management(request.user),
    })


@login_required
def claim_item(request, item_type, item_id):
    if request.method != 'POST':
        return redirect('user_home_page')

    model = {'lost': LostItem, 'found': FoundItem}.get(item_type)
    if model is None:
        return HttpResponseForbidden('Unknown item type.')

    item = get_object_or_404(model, item_id=item_id)

    if item.status == ItemStatus.OPEN:
        item.status = ItemStatus.CLAIMED
        item.claimed_by = request.user
        item.save()
        notify_express('item_claimed', {
            'type': item_type,
            'id': item.item_id,
            'name': item.name,
            'claimed_by': request.user.username,
        })
        messages.success(request, f'You claimed "{item.name}". Management will verify your request.')
    else:
        messages.error(request, f'"{item.name}" is no longer available to claim.')

    return redirect('found_items' if item_type == 'found' else 'lost_items')


@login_required
@management_required
def resolve_item(request, item_type, item_id):
    model = {'lost': LostItem, 'found': FoundItem}.get(item_type)
    if model is None:
        return HttpResponseForbidden('Unknown item type.')

    if request.method != 'POST':
        return redirect('found_items' if item_type == 'found' else 'lost_items')

    item = get_object_or_404(model, item_id=item_id)

    # Allow resolving if it's Open or Claimed
    if item.status in [ItemStatus.OPEN, ItemStatus.CLAIMED]:
        # If it's a Lost Item, create the Found Item automatically
        if item_type == 'lost':
            try:
                # Check if this has already been transferred to prevent duplicates
                existing = FoundItem.objects.filter(name=item.name, location_found=item.location_lost).exists()
                if not existing:
                    found_item = FoundItem(
                        name=item.name,
                        description=f"[Transferred from Lost Report] {item.description}",
                        date_found=timezone.now().date(),
                        location_found=item.location_lost,
                        status=ItemStatus.RESOLVED, # Marked as resolved
                        reported_by=request.user
                    )
                    
                    # Safely copy the image reference
                    if item.image:
                        found_item.image.name = item.image.name
                        
                    found_item.save()
                
                notify_express('item_transferred', {'name': item.name, 'location': item.location_lost})
                messages.success(request, f'"{item.name}" has been marked as resolved and moved to the Found Items page.')
            except Exception as e:
                # If it fails, show the exact error message so we know why
                messages.error(request, f"Failed to transfer to found items: {str(e)}")
                return redirect('lost_items')
        else:
            notify_express('item_resolved', {'type': item_type, 'id': item.item_id, 'name': item.name})
            messages.success(request, f'"{item.name}" has been marked as resolved.')

        # Update the current item's status
        item.status = ItemStatus.RESOLVED
        item.save()

    else:
        messages.error(request, f'This item is already resolved.')

    return redirect('found_items' if item_type == 'found' else 'lost_items')


@login_required
def user_home_page(request):
    my_lost_reports = LostItem.objects.filter(reported_by=request.user).order_by('-created_at')
    my_found_reports = FoundItem.objects.filter(reported_by=request.user).order_by('-created_at')
    my_claims = ClaimRequest.objects.filter(requester=request.user).order_by('-created_at')

    return render(request, 'user_home_page.html', {
        'my_lost_reports': my_lost_reports,
        'my_found_reports': my_found_reports,
        'my_claims': my_claims,
        'is_management': is_management(request.user),
    })
    
@login_required
def submit_claim_request(request, item_type, item_id):
    # 1. Must be a POST request
    if request.method != 'POST':
        return redirect('user_home_page')

    # 2. Block claiming of Found items entirely (as we discussed)
    if item_type == 'found':
        messages.error(request, "You cannot claim items from the Found Items page.")
        return redirect('found_items')

    # 3. Validate the item type
    model = {'lost': LostItem, 'found': FoundItem}.get(item_type)
    if not model:
        return HttpResponseForbidden('Unknown item type.')
        
    item = get_object_or_404(model, item_id=item_id)

    # 4. Check if the item is still available
    if item.status != ItemStatus.OPEN:
        messages.error(request, "This item is no longer available to claim.")
        return redirect('lost_items')

    # 5. Validate the form
    form = ClaimRequestForm(request.POST)
    
    if form.is_valid():
        # Check if user already has a pending request for this item
        existing = ClaimRequest.objects.filter(
            item_type=item_type, 
            item_id=item_id, 
            requester=request.user, 
            status='Pending'
        ).exists()
        
        if existing:
            messages.warning(request, "You already have a pending request for this item.")
            return redirect('lost_items')

        # Save the claim request
        claim = form.save(commit=False)
        claim.item_type = item_type
        claim.item_id = item_id
        claim.requester = request.user
        claim.save()

        notify_express('claim_requested', {
            'item_type': item_type, 
            'item_id': item_id, 
            'name': item.name, 
            'requester': request.user.username
        })
        
        messages.success(request, f"Your claim request for '{item.name}' has been sent to management.")
        return redirect('user_home_page')

    # 6. THIS IS THE CRITICAL FALLBACK: 
    # If the form is invalid (e.g., they left the reason blank), we redirect back with an error.
    messages.error(request, "Failed to submit claim. Please provide a valid reason.")
    return redirect('lost_items')

@login_required
@management_required
def management_requests(request):
    # Managers can see all pending requests here
    pending_requests = ClaimRequest.objects.filter(status='Pending').order_by('-created_at')
    history_requests = ClaimRequest.objects.exclude(status='Pending').order_by('-created_at')[:20]

    return render(request, 'management_requests.html', {
        'pending_requests': pending_requests,
        'history_requests': history_requests,
    })

@login_required
@management_required
def process_claim_request(request, req_id, action):
    if request.method != 'POST':
        return redirect('management_requests')

    claim_req = get_object_or_404(ClaimRequest, id=req_id)
    if claim_req.status != 'Pending':
        messages.error(request, "This request has already been processed.")
        return redirect('management_requests')

    note = request.POST.get('manager_note', '').strip()
    model = {'lost': LostItem, 'found': FoundItem}.get(claim_req.item_type)
    item = get_object_or_404(model, item_id=claim_req.item_id)

    if action == 'approve':
        claim_req.status = 'Approved'
        claim_req.manager_note = note
        claim_req.save()

        # Update item status
        item.status = ItemStatus.CLAIMED
        item.claimed_by = claim_req.requester
        item.save()

        # Decline all other pending requests for this item
        ClaimRequest.objects.filter(item_type=claim_req.item_type, item_id=claim_req.item_id, status='Pending').exclude(id=req_id).update(status='Declined', manager_note="Item was claimed by another user.")
        
        notify_express('claim_approved', {'name': item.name, 'user': claim_req.requester.username})
        messages.success(request, f"Approved claim for {item.name}.")

    elif action == 'decline':
        claim_req.status = 'Declined'
        claim_req.manager_note = note
        claim_req.save()
        
        notify_express('claim_declined', {'name': item.name, 'user': claim_req.requester.username})
        messages.success(request, f"Declined claim for {item.name}.")

    return redirect('management_requests')

# ─────────────────────────────────────────────────────────────────
# QR Code & Verification System
# ─────────────────────────────────────────────────────────────────
@login_required
def claim_qr_code(request, req_id):
    """Generates a QR code image for an approved claim."""
    req = get_object_or_404(ClaimRequest, id=req_id, requester=request.user, status='Approved')
    
    # Build the public verification URL (e.g., http://localhost:8000/verify/5/)
    verify_url = request.build_absolute_uri(reverse('verify_claim', args=[req.id]))
    
    # Generate QR code
    img = qrcode.make(verify_url)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    
    return HttpResponse(buffer.getvalue(), content_type="image/png")


def verify_claim(request, req_id):
    """Public page accessed when a QR code is scanned."""
    # We allow anyone to view this if they have the link (like a physical ticket)
    req = get_object_or_404(ClaimRequest, id=req_id, status='Approved')
    
    context = {
        'username': req.requester.username,
        'id_number': req.requester.id_number,
        'item_name': req.get_item_name(),
        'item_type': req.item_type,
    }
    return render(request, 'verify_claim.html', context)