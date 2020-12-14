# SI507-Final-Project: Allrecipes to Kroger Cart

This program is meant to make it easier to go from a recipe idea to a Kroger cart. 

The program will ask the user to enter a recipe query pertaining to the site https://www.allrecipes.com/. If the query exists, the program will return 20 recipes. The user can view the ingredients for any of the recipes and confirm one-by-one whether they already own the ingredients. If the user wants to add the ingredients that they don't own to a Kroger cart, they must briefly authenticate using OAuth2. The program will then add the items to the cart. The user will also have the option of viewing recipe-related plots. The user can move back, move on, or exit at any stage. 

Currently, the program only supports a command line interface. 

## Acquiring Keys from Kroger API
Kroger API keys can be acquired from https://developer.kroger.com/. You will also need to specify a redirect URI, where you will receive an authorization code during API authentization. You should request Cart and Product permissions in the Production Environment https://api.kroger.com/v1/. For API authentication, Kroger uses the OAuth2 protocol (RFC6749), supporting the Authorization Code, Client Credentials, and Refresh Token grant types. More information can be found here: https://developer.kroger.com/reference/. 

## Secrets
Store API keys and redirect URI in a file called 'secrets.py'. The secrets file will be imported in the main program file.
Use the following format and enter your own keys and redirect URI: 

```
KROGER_CLIENT_ID= ""
KROGER_CLIENT_SECRET=""
REDIRECT_URI = ""
```

## Requirements
Use the package manager pip to install packages.

```
pip install beautifulsoup4
```
```
pip install bs4
```
```
pip install chart-studio
```
```
pip install gensim
```
```
pip install matplotlib
```
```
pip install oauthlib
```
```
pip install plotly
```
```
pip install requests
```
```
pip install requests-oauthlib
```
```
pip install wordcloud
```

## Plots
There are five options for the recipe related plots.

1. Nutrition Information (all recipes in query)
2. Ratings vs. Reviews Numbers (all recipes in query)
3. Number of Steps in Recipe by Rating Score (all recipes in query)
4. Allergen Information (all recipes in query)
5. Common Words in Reviews (previously chosen recipe)

## Support
If you have any issues, comments, or questions please contact wernerck@umich.edu.
