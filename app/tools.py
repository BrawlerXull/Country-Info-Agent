import httpx
from typing import Dict, Any, Optional
from langfuse import observe

@observe(as_type="generation")
def fetch_country_info(country_name: str) -> Dict[str, Any]:
    """
    Fetches country information from the REST Countries API.
    
    Args:
        country_name: The name of the country to look up.
        
    Returns:
        A dictionary containing country data or an error message.
    """
    base_url = "https://restcountries.com/v3.1/name"
    
    try:
        # Strategy 1: Attempt Exact Match
        # This solves the "India" -> "British Indian Ocean Territory" issue immediately if the user types "India"
        url_exact = f"{base_url}/{country_name}?fullText=true"
        
        with httpx.Client() as client:
            response = client.get(url_exact, timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                     return {"status": "success", "data": data[0]}

            # Strategy 2: Fallback to Partial Match with Intelligent Filtering
            # If exact match fails (e.g. "USA" might not match unless it's an alt spelling, or user made a typo),
            # we try the standard search.
            url_partial = f"{base_url}/{country_name}"
            response = client.get(url_partial, timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                
                if isinstance(data, list) and len(data) > 0:
                    # Filter for best match
                    # 1. Look for exact match in common/official name
                    for country in data:
                        name = country.get("name", {})
                        common = name.get("common", "").lower()
                        official = name.get("official", "").lower()
                        query_lower = country_name.lower()
                        
                        if common == query_lower or official == query_lower:
                            return {"status": "success", "data": country}
                    
                    # 2. Look for exact match in altSpellings
                    for country in data:
                        alt = [a.lower() for a in country.get("altSpellings", [])]
                        if country_name.lower() in alt:
                             return {"status": "success", "data": country}
                             
                    # 3. Default fallback: Return the first result
                    return {"status": "success", "data": data[0]}
                    
                else:
                     return {"status": "error", "message": "No data found for this country."}
            
            elif response.status_code == 404:
                return {"status": "error", "message": f"Country '{country_name}' not found."}
            else:
                return {"status": "error", "message": f"API Error: {response.status_code}"}
                
    except httpx.RequestError as e:
        return {"status": "error", "message": f"Network error occurred: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}
