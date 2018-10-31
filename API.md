API documentation

# Get addon recommendations

Allow the Authenticated User to update their details.

**URL** : `/v1/api/recommendations/<hashed_id>/`

**Method** : `POST`

**Auth required** : NO

**Permissions required** : None

**Data constraints**

```json
{
    "options": {"promoted": [
                                ["[1 to 30 chars]", Some Number],
                                ["[1 to 30 chars]", Some Number],
                            ]
               }
}
```

Note that the only valid key for the top level JSON is `options`.

`options` is always a dictionary of optional values.  

To denote no optional data - it is perfectly valid for the JSON data
to have no `options` key, or even simpler - not have POST data at all.

Each item in the promoted addon GUID list is accompanied by an
integer weight.  Any weight is greater than a TAAR recommended addon
GUID.

**Data examples**

Partial data is allowed.

```json
{
    "options": {"promoted": [
                                ["guid1", 10],
                                ["guid2", 5],
                            ]
               }
}
```


## Success Responses

**Condition** : Data provided is valid

**Code** : `200 OK`

**Content example** : Response will reflect a list of addon GUID suggestions.

```json
{
    "results": ["taar-guid1", "taar-guid2", "taar-guid3"],
    "result_info": [],
}
```

## Error Response

**Condition** : If provided data is invalid, e.g. options object is not a dictionary.

**Code** : `400 BAD REQUEST`

**Content example** :

```json
{
    "invalid_option": [
        "Please provide a dictionary with a `promoted` key mapped to a list of promoted addon GUIDs",
    ]
}
```

## Notes

* Endpoint will ignore irrelevant and read-only data such as parameters that
  don't exist, or fields.
* Endpoint will try to fail gracefully and return an empty list in the
  results key if no suggestions can be made.
* The only condition when the endpoint should return an error code if
  the options data is malformed.



