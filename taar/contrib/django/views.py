from django.core.cache import cache
from django.shortcuts import render
import requests

from taar.recommenders import RecommendationManager
from .forms import AddonRecommendationsForm

ADDON_MAPPING_URL = ("https://s3-us-west-2.amazonaws.com/"
                     "telemetry-public-analysis-2/telemetry-ml/"
                     "addon_recommender/addon_mapping.json")


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
            error_text = ""
            addon_mapping = cache.get('addon_mapping', {})
            if not addon_mapping:
                try:
                    response = requests.get(ADDON_MAPPING_URL)
                    response.raise_for_status()
                    addon_mapping = response.json()
                except:
                    error_text = ("It wasn't possible to retrieve"
                                  "the list of addons")
                cache.set('addon_mapping', addon_mapping)
            recommendations_names = [addon_mapping.get(r, "")
                                     for r in recommendations]
    context = {
        'form': form,
        'recommendations': recommendations_names,
        'error_text': error_text
    }

    return render(request, template_name="taar/index.html", context=context)
