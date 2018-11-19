# TAAR: Data Collection Policy
Data collection policy and opt-out mechanisms pertaining to the Telemetry-Aware Addon Recommender (TAAR) service.

Table of Contents (ToC):
===========================

* [Overview](#overview)
* [Technical details](#technical-details)
	* [Client-side](#client-side-data-collection)
	* [Server-side](#data-collected-from-the-taar-server)
* [Opt-out mechanisms](#opt-out-mechanisms-for-taar)
* [Privacy considerations](#privacy-considerations)

## Overview
To better predict what extensions you may find interesting, Firefox uses the telemetry-Aware Add-on Recommender (TAAR) system—a Mozilla service that recommends extensions by examining basic browser telemetry. This means TAAR analyzes usage statistics from a large number of other Firefox users, looks at other extensions you may have installed, and considers general characteristics about your Firefox profile (like language preference). Based on this information, TAAR surfaces extension recommendations tailored just for you. 

Extensions allow you to add features to Firefox to customize your browsing experience. Extensions are software programs, most often developed by a third party, that modify the way Firefox works.

## Technical details
In order to associate a client's existing telemetry data to a [TAAR-API](https://github.com/mozilla/taar-api) request during a browser session a one way [sha256 hash](https://en.wikipedia.org/wiki/SHA-2) of the [telemetry client_id](https://firefox-source-docs.mozilla.org/toolkit/components/telemetry/telemetry/data/common-ping.html) is exposed via a specific [TAAR preference](https://bugzilla.mozilla.org/show_bug.cgi?id=1499470). This preference can be enabled/disabled via the `about:preferences` page in Firefox. The hashed client_id allows us to use a subset of Firefox telemetry data sources to build models that can be used to make Web Extension recommendations based (in part) on telemetry.

### Client-side data collection
The following data collection is implemented on the _client_

* one-way hashed telemetry client_id: sha256(client_id)

### Data collected from the TAAR server
Note: this data is logged once a successful lookup has been performed associating a hashed client_id with a previously seen hashed client_id. The complete list of fields below is only collected in the the case that a successful response (including a set of recommendations has been has been made). This data is not from the client nor is it accessible by the client. It's included here for completeness.

* timestamp (a timestamp object: system timestamp for the taar request)
* taar.model (a string value: indicating the current version of the taar service and the model used)
* logger.identifier (a string value: logger name, should always be "srg.taar")
* hashed_client_id (a string value: the same hashed clientId as is exposed to AMO)
* model_parameters (list of floats: necessary parameters for operating and diagnosing TAAR operation)
* guids_recommended (a list of strings: the list of guids that were served as recommendations for that taar request)

## Opt-out mechanisms for TAAR
To turn off personalized recommendations in the Add-ons Manager, visit [hamburger menu] > Preferences  > Data Collection and Use, and un-check the box that reads, “Allow Firefox to make personalized extension recommendations.”

If you opt out, you’ll still see generalized recommended extensions in the Add-ons Manager, however they won’t be personally tailored for you using telemetry data. 

The TAAR service will not log any information while a client session is in [Private Browsing Mode](https://support.mozilla.org/en-US/kb/private-browsing-use-firefox-without-history).

## Privacy considerations
All data collected by the TAAR service adhere to Mozilla's [Data Collection guidelines](https://wiki.mozilla.org/Firefox/Data_Collection). No Personally Identifiable information (PII) is collected by the TAAR-service and raw data collected by the TAAR service is never joined against other derived datasets. 

A data retention period of (180 days) for the raw data applies to all client and server side data collected by the TAAR service. Anonymised aggregates based on this data may be stored indefinitely. Aggregates derived from the collected data will be used for monitoring the health fo the Web Extensions ecosystem. System logs will be used to diagnose problems with the TAAR core technology. 

Data collection and retention decisions related to the development of the TAAR services are driven by the [Mozilla Privacy Principles](https://www.mozilla.org/en-US/privacy/principles/) and strive to provide transparent 

Recommendations are strictly intended to provide a better browsing experience for Firefox users. As described above, extension developers cannot pay for placement in the recommendation program, and Firefox does not receive any compensation as a result of this process.
