# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import colander


class ExtraDataSchema(colander.MappingSchema):
    branch = colander.SchemaNode(colander.String(),
                                 validator=colander.OneOf(['linear',
                                                           'control',
                                                           'ensemble']))


class RecommendationManagerQuerySchema(colander.MappingSchema):
    """
    This schema validates that arguments passed into
    `RecommendationManager::recommend` are of the correct type.

    Mostly useful for evoloving unittests and APIs in a stable way.
    """
    client_id = colander.SchemaNode(colander.String(),
                                    validator=colander.Length(max=200))
    limit = colander.SchemaNode(colander.Int(),
                                missing=10,
                                validator=colander.Range(min=1, max=100))
    extra_data = ExtraDataSchema()
