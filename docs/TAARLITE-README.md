# Taar-lite

The TAAR-lite service has been merged into the main TAAR repository
now.

TAAR-lite exposes a GUID-GUID recommender that recommends addons based
on the co-installation rate of each accept-list addons with other
accept listed addons.


#### ETL workflow AMO guid-guid TAAR-lite
* [taar_amodump.py](https://github.com/mozilla/taar_gcp_etl/blob/master/taar_etl/taar_amodump.py)
	* Scheduled to run daily
	* Collects all listed addons by callign the [AMO public API](https://addons.mozilla.org/api/v3/addons/search/) endpoint
	* Applies filter returning only Firefox Web Browser Extensions
	* Writes __extended_addons_database.json__
* [taar_amowhitelist.py](https://github.com/mozilla/taar_gcp_etl/blob/master/taar_etl/taar_amowhitelist.py)
	* Scheduled to run daily, dependent on successful completion of [taar_amodump.py](https://github.com/mozilla/taar_gcp_etl/blob/master/taar_etl/taar_amodump.py)
	* Filters the addons contained in __extended_addons_database.json__
		* removes legacy addons
		* removes Web Extensions with a rating < 3.0
		* removes Web Extensions uploaded less than 60 days ago
		* removes [Firefox Pioneer](https://addons.mozilla.org/en-GB/firefox/addon/firefox-pioneer/?src=search)
	* Writes __whitelist_addons_database.json__
* [taar_lite_guidguid.py](https://github.com/mozilla/taar_gcp_etl/blob/master/taar_etl/taar_lite_guidguid.py)
	* Computes the coinstallation rate of each whitelisted addon with other whitelisted addons for a sample of Firefox clients
	* Removes rare combinations of coinstallations 
	* writes __guid_coinstallation.json__

## Build and run tests

The main TAAR build and test instructions are applicable as this is
now a unified codebase.
