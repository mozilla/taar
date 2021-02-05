# Emulate package call from Ensemble Spark job


COLLABORATIVE, SIMILARITY, LOCALE = "collaborative", "similarity", "locale"
PREDICTOR_ORDER = [COLLABORATIVE, SIMILARITY, LOCALE]


def load_recommenders():
    from taar.recommenders import LocaleRecommender
    from taar.recommenders import SimilarityRecommender
    from taar.recommenders import CollaborativeRecommender
    from taar.context import package_context

    ctx = package_context()

    lr = LocaleRecommender(ctx)
    sr = SimilarityRecommender(ctx)
    cr = CollaborativeRecommender(ctx)
    return {LOCALE: lr, COLLABORATIVE: cr, SIMILARITY: sr}


if __name__ == '__main__':
    for i in range(2):
        rec_map = load_recommenders()

        recommender_list = [
            rec_map[COLLABORATIVE].recommend,  # Collaborative
            rec_map[SIMILARITY].recommend,  # Similarity
            rec_map[LOCALE].recommend,  # Locale
        ]

        client_data = {"installed_addons": ["uBlock0@raymondhill.net"],
                       "locale": "en-CA",
                       "client_id": "test-client-001",
                       "activeAddons": [],
                       "geo_city": "brasilia-br",
                       "subsession_length": 4911,
                       "os": "mac",
                       "bookmark_count": 7,
                       "tab_open_count": 4,
                       "total_uri": 222,
                       "unique_tlds": 21
                       }

        for key, rec in rec_map.items():
            print(key)
            assert rec.can_recommend(client_data)
            assert len(rec.recommend(client_data, limit=4)) == 4
