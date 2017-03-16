from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .forms import AddonRecommendationsForm
from taar.recommenders import RecommendationManager


@login_required
def get_client_recommendations(request):
    form = AddonRecommendationsForm()
    recommendations = []
    if request.method == 'POST':
        form = AddonRecommendationsForm(data=request.POST)
        if form.is_valid():
            # Use addon recommender.
            value = form.cleaned_data['client_id']
            recommendation_manager = RecommendationManager()
            recommendations = recommendation_manager.recommend(value, 10)
    context = {
        'form': form,
        'recommendations': recommendations
    }

    return render(request, template_name="taar/index.html", context=context)
