##################################
##### Name: Christian Werner #####
##### Uniqname: wernerck     #####
##################################

# import
import sys
import json
import sqlite3
import webbrowser
import time
import secrets # file that contains API keys

# parsing
import bs4
from bs4 import BeautifulSoup
from string import punctuation, digits 

# authorization
import requests
from requests.auth import HTTPBasicAuth
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

# visualization
import plotly
import plotly.graph_objects as go
import chart_studio.plotly as py
import matplotlib.pyplot as plt
from gensim.parsing.preprocessing import remove_stopwords
from wordcloud import WordCloud

# Request headers
headers = {
    "User-Agent": "UMSI 507 Course Project - Python Scraping",
    "From": "wernerck@umich.edu",
    "Course-Info": "https://si.umich.edu/programs/courses/507"
}

# API 
client_key = secrets.KROGER_CLIENT_ID # from secrets
client_secret = secrets.KROGER_CLIENT_SECRET # from secrets
redirect = secrets.REDIRECT_URI # from secrets

# CACHE
CACHE_FILE_NAME = "cache_recipes.json"
CACHE_DICT = {}

# KROGER CACHE
CACHE_FILE_K = "cache_kroger.json"
CACHE_DICT_K = {}

# SECRET CACHE: for the refreshable tokens
CACHE_FILE_S = "cache_secret.json" # tokens will expire, but still should not be shared
CACHE_DICT_S = {}

class Recipe:
    '''A recipe from allrecipes.com

    Instance Attributes
    -------------------
    name: string
        the name of a recipe (e.g. "Chocolate Cake')
    rating: float or int
        the rating of a recipe out of 5 (e.g. 4.67, "")
        some ratings are blank
    num_rating: string or int
        the rating of a recipe (e.g. "1,550", 0)
        some recipes are not rated
    directions: string
        the rating of a recipe (e.g. "[1] Preheat the oven... ", "")
        some directions are blank
    num_steps: int
        the number of steps to make a recipe (e.g. 7, ...)
        some steps are blank
    review: string
        the top reviews of a recipe (e.g. "This recipe was very good...", "")
        some reviews are blank
    num_review: string or int
        the number of reviews of a recipe (e.g. "1,110", 0)
        some recipes are not reviewed
    servings: int
        the servings of a recipe (e.g. 16)
    ingredients: string
        the ingredients of a recipe (e.g. "2 cups flour", "1 cup water")
    nutrition: string
        the nutritional information of a recipe (e.g. "412 calories; protein 6.8g...", "")
        some nutritional information is blank
    '''
    # Class constants to parse HTML
    NAME_DIV_CLASS = "headline-wrapper"
    NAME_CONTAINER_TAG = "h1"
    RATING_DIV_CLASS = "recipe-review-container euDisabled"
    RATING_DIV_CONTAINER = "span"
    NUMRAT_DIV_CLASS = "partial ugc-ratings"
    NUMRAT_DIV_CONTAINER = "span" 
    DIR_SECTION_CLASS = "recipe-instructions recipe-instructions-new component container"
    DIR_SECTION_CONTAINER = "p"
    NUMSTEP_SECTION_CLASS = "recipe-instructions recipe-instructions-new component container"
    NUMSTEP_CONTAINER_CLASS = "checkbox-list-text"
    REVIEW_DIV_CLASS = "recipes-reviews-container container"
    REVIEW_DIV_CONTAINER = "span"
    NUMREV_DIV_CLASS = "partial ugc-ratings"
    NUMREV_DIV_CONTAINER = "a"    
    SERV_DIV_CLASS = "recipe-meta-item-body"
    INGREDIENTS_DIV_CLASS = "recipe-shopper-wrapper"
    INGREDIENTS_CONTAINER_TAG = "span"
    NUTRITION_DIV_CLASS = "nutrition-section container"
    NUTRITION_CONTAINER_TAG = "div"   

    def __init__(self, url, details_soup):
        self.url = url
        self.name = self.extract_name(details_soup)
        self.rating = self.extract_rating(details_soup)
        self.num_rating = self.extract_num_rating(details_soup)
        self.directions = self.extract_directions(details_soup)
        self.num_steps = self.extract_num_steps(details_soup)
        self.review = self.extract_review(details_soup)
        self.num_review = self.extract_num_review(details_soup)
        self.servings = self.extract_servings(details_soup)
        self.ingredients = self.extract_ingredients(details_soup)
        self.nutrition = self.extract_nutrition(details_soup)

    def extract_name(self, soup):
        nam = (soup.find(class_=self.NAME_DIV_CLASS)
        .find(self.NAME_CONTAINER_TAG)
        .next_element
        .string)
        return nam

    def extract_rating(self, soup):
        try: # use try/catch in case rating is missing
            rat = (soup.find(class_=self.RATING_DIV_CLASS)
            .find(self.RATING_DIV_CONTAINER, class_="review-star-text")
            .string
            .strip()
            .split(":")[1]
            .split()[0])
            return rat
        except:
            return "No rating"

    def extract_num_rating(self, soup):
        try: # use try/catch in case missing
            nrat = (soup.find(class_=self.NUMRAT_DIV_CLASS))
            nums = []
            nums_2 = []
            for n in nrat.find_all(self.NUMRAT_DIV_CONTAINER, class_="ugc-ratings-item"):
                nstr = n.string
                nbrack = nstr.strip().split()
                nums.append(nbrack)
                for nu in nums:
                    for num in nu:
                        if num == "Ratings":
                            pass
                        else:
                            nums_2.append(num)
            return nums_2[0]
        except:
            return 0

    def extract_directions(self, soup):
        try: # use try/catch in case missing
            ndir = (soup.find(class_=self.DIR_SECTION_CLASS))
            dirs = []
            count = 1
            for nd in ndir.find_all(self.DIR_SECTION_CONTAINER):
                nstr = nd.string
                step = "[" + str(count) + "] " + nstr
                count += 1
                dirs.append(step)
            return dirs
        except:
            return "No Directions"

    def extract_num_steps(self, soup):
        try: # use try/catch in case missing
            nstep = (soup.find(class_=self.NUMSTEP_SECTION_CLASS))
            for n in nstep.find_all(class_=self.NUMSTEP_CONTAINER_CLASS): # using nbrack bc only need the last step number
                nstr = n.string
                nbrack = nstr.strip().split()
            return nbrack[1]
        except:
            return "N/A"

    def extract_review(self, soup): # from the first page
        try: # use try/catch in case review is missing
            rev = (soup.find(class_=self.REVIEW_DIV_CLASS))
            revs = []
            for n in rev.find_all(self.REVIEW_DIV_CONTAINER, class_="recipe-review-body--truncated"):
                nstr = n.string
                nbrack = nstr.split("\n")
                good = nbrack[3].strip()
                revs.append(good)
            return revs
        except:
            return "No reviews"

    def extract_num_review(self, soup):
        try: # use try/catch in case missing
            nrev = (soup.find(class_=self.NUMREV_DIV_CLASS)) #
            nums = []
            nums_2 = []
            for n in nrev.find_all(self.NUMREV_DIV_CONTAINER, class_="ugc-ratings-link ugc-reviews-link"):
                nstr = n.string
                nbrack = nstr.strip().split()
                nums.append(nbrack)
                for nu in nums:
                    for num in nu:
                        if num == "Reviews":
                            pass
                        else:
                            nums_2.append(num)
            return nums_2[0]
        except:
            return 0

    def extract_servings(self, soup):
        serv = (soup.find_all(class_=self.SERV_DIV_CLASS))
        serving = []
        for s in serv:
            sstr = s.string
            small = sstr.strip()
            small = small.replace(" ", "")
            try:
                small = int(small)
                serving.append(small)
            except:
                ValueError
                continue
        return serving[0] # list with 1 number, the serving for this recipe

    def extract_ingredients(self, soup):
        ing = (soup.find(class_=self.INGREDIENTS_DIV_CLASS)
        .find_all(self.INGREDIENTS_CONTAINER_TAG, class_="ingredients-item-name"))
        ingrs = []
        for i in ing:
            ingrs.append(i.string.strip())
        return ingrs

    def extract_nutrition(self, soup):
        try: # use try/catch in case a recipe is missing nutritional info
            nut = (soup.find(class_=self.NUTRITION_DIV_CLASS))
            for n in nut.find_all(self.NUTRITION_CONTAINER_TAG, class_="section-body"):
                nstr = str(n)
                nbrack = nstr.split("\n")
                good = nbrack[1].strip()
                goods = good.split(";")
                
                for i in range(len(goods)):
                    goods[i] = goods[i].strip().capitalize()
                    if i == len(goods) - 1:
                        goods[i] = goods[i][:-1]
            return goods
        except:
            return "No nutrition information"

    def info(self): # info.self() to be displayed in interactive search
        return str(self.name) + " (" + str(self.num_steps) + " Steps): " + str(self.rating) + " Stars"

class Product():
    '''Product within Kroger.

    Instance Attributes
    ----------
    upc: string
        The upc of the product
        upc is needed for cart
    brand: string
        The brand of the product
    categories: string
        The categories of the product
    description: string
        The decription of the product
    limit: int
        The return limit of the product
    json: json dict
        The json result for the product
    '''
    def __init__(self, upc="No upc", brand="No brand", categories="No categories", description="No description", limit="No limit value", json="None"):
        if json == "None":
            self.upc = upc
            self.brand = brand
            self.categories = categories
            self.description = description
            self.limit = limit
        
        if json != "None":
            try:
                self.upc = json["data"][0]["upc"]
            except (IndexError, KeyError):
                self.upc = None
            try:
                self.brand = json["data"][0]["brand"]
            except (IndexError, KeyError):
                self.brand = None
            try: 
                self.categories = json["data"][0]["categories"]
            except (IndexError, KeyError):
                self.categories = None
            try:
                self.description = json["data"][0]["description"]
            except (IndexError, KeyError):
                self.description = None
            try:
                self.limit = json["meta"]["pagination"]["limit"]
            except (IndexError, KeyError):
                self.limit = None

def create_tables():
    conn = sqlite3.connect("recipe.sqlite")
    cur = conn.cursor()

    create_recipes = '''
        CREATE TABLE IF NOT EXISTS "recipes" (
            "recipe_name" TEXT PRIMARY KEY NOT NULL UNIQUE,
            "query" TEXT NOT NULL,
            "url" TEXT NOT NULL,
            "number_of_steps" INTEGER NOT NULL,
            "directions" TEXT NOT NULL,
            "rating_out_of_5" TEXT NOT NULL,
            "total_number_ratings" INTEGER NOT NULL
        );
    '''

    create_ingredients = '''
        CREATE TABLE IF NOT EXISTS "ingredients" (
            "recipe" TEXT PRIMARY KEY NOT NULL UNIQUE,
            "query" TEXT NOT NULL,
            "ingredients" TEXT NOT NULL,
            "servings" INTEGER NOT NULL, 
            "nutrition_per_serving" TEXT NOT NULL,
            FOREIGN KEY (recipe) REFERENCES recipes (recipe_name)
        );
    '''

    create_reviews = '''
        CREATE TABLE IF NOT EXISTS "reviews" (
            "recipe" TEXT PRIMARY KEY NOT NULL UNIQUE,
            "query" TEXT NOT NULL,
            "top_reviews" TEXT NOT NULL,
            "total_number_reviews" INTEGER NOT NULL, 
            FOREIGN KEY (recipe) REFERENCES recipes (recipe_name)
        );
    '''

    create_cart = '''
        CREATE TABLE IF NOT EXISTS "cart" (
            "upc" TEXT PRIMARY KEY NOT NULL UNIQUE,
            "ingredient_query" TEXT NOT NULL,
            "original_ingredients_list" TEXT NOT NULL,
            "brand" TEXT NOT NULL,
            "categories" TEXT NOT NULL,
            "description" TEXT NOT NULL,
            "limit" INTEGER NOT NULL, 
            FOREIGN KEY (original_ingredients_list) REFERENCES ingredients (ingredients)
        );
    '''

    cur.execute(create_recipes)
    cur.execute(create_ingredients)
    cur.execute(create_reviews)
    cur.execute(create_cart)
    conn.commit()

def add_to_recipe_table(recipe_data_list):
    conn = sqlite3.connect("recipe.sqlite")
    cur = conn.cursor()
    insert_recipes = '''
        INSERT OR IGNORE INTO recipes
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT DO NOTHING;
    '''
    cur.execute(insert_recipes, recipe_data_list)
    conn.commit()

def add_to_ingredients_table(ingredients_data_list):
    conn = sqlite3.connect("recipe.sqlite")
    cur = conn.cursor()
    insert_ingredients = '''
        INSERT OR IGNORE INTO ingredients
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT DO NOTHING;
    '''
    cur.execute(insert_ingredients, ingredients_data_list)
    conn.commit()

def add_to_reviews_table(reviews_data_list):
    conn = sqlite3.connect("recipe.sqlite")
    cur = conn.cursor()
    insert_reviews = '''
        INSERT OR IGNORE INTO reviews
        VALUES (?, ?, ?, ?)
        ON CONFLICT DO NOTHING;
    '''
    cur.execute(insert_reviews, reviews_data_list)
    conn.commit()

def add_to_cart_list_table(cart_data_list):
    conn = sqlite3.connect("recipe.sqlite")
    cur = conn.cursor()
    insert_cart = '''
        INSERT OR IGNORE INTO cart
        VALUES (?, ?, ?, ?, ?, ?, ?);
    '''
    cur.execute(insert_cart, cart_data_list)
    conn.commit()

def pull_from_db(query):
    conn = sqlite3.connect("recipe.sqlite")
    cur = conn.cursor()
    # sub in query from main
    result = cur.execute(query).fetchall()
    conn.close()
    return result

def build_recipe_url_dict():
    ''' Make a dictionary that maps recipe name to recipe page url from "https://www.allrecipes.com/"

    Parameters
    ----------
    None

    Returns
    -------
    dict
        key is a recipe name and value is the url
        e.g. {"cake": ["https://www.allrecipes.com/recipe/25642/white-chocolate-raspberry-cheesecake/", ...}
    '''
    BASE_URL = "https://www.allrecipes.com/search/results/" 
 
    # queries > 1 word are treated differently
    special = "%20" # after the first word append "%20" to the beginning of each word
    empty_query = ""

    if len(recipe_query) > 1:
        r = recipe_query.split()
        empty_query += r[0]
        for i in range(1, len(r)):
            j = special + r[i]
            empty_query += j
    
    else: 
        empty_query = recipe_query

    # create params dictionary
    params = {}
    params["wt"] = empty_query
    params["sort"] = "p" # sort by popular recipes

    param_strings = []
    for k in params:
        param_strings.append("{}={}".format(k, params[k]))
    recipe_page_url = BASE_URL + "?" + "&".join(param_strings)

    # BeautifulSoup parsing
    response = requests.get(recipe_page_url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser") # Make the soup
    recipes = {}
    
    recipes_query_list = [] 
    recipe_list_parent = soup.find_all("div", id="searchResultsApp") # to parse recipe list for crawling
    for tag in recipe_list_parent:
        for recipe_link_parent_tag in tag.find_all("article", class_="fixed-recipe-card"):
            recipe_link_tag = recipe_link_parent_tag.find("div", class_="fixed-recipe-card__info")
            for t in recipe_link_tag:
                recipe_link = t.find("a")
                if type(recipe_link) == bs4.element.Tag:
                    linkdata = recipe_link.get("href")
                    if linkdata[:34] == "https://www.allrecipes.com/recipe/":
                        recipes_query_list.append(linkdata)
    recipes[recipe_query] = recipes_query_list      
    return recipes

### CACHING ###
def load_cache(cache_fname):
    ''' Opens the cache file if it exists and loads the JSON into
    the CACHE_DICT dictionary. If the cache file doesn't exist, 
    creates a new cache dictionary.
    
    Parameters
    ----------
    None
    
    Returns
    -------
    dict
        the opened cache
    '''
    try:
        cache_file = open(cache_fname, "r")
        cache_file_contents = cache_file.read()
        cache = json.loads(cache_file_contents)
        cache_file.close()
    except:
        cache = {}
    return cache

def save_cache(cache, cache_fname):
    ''' Saves the current state of the cache to disk
    
    Parameters
    ----------
    cache_dict: dict
        The dictionary to save
    
    Returns
    -------
    None
    '''
    cache_file = open(cache_fname, "w")
    contents_to_write = json.dumps(cache)
    cache_file.write(contents_to_write)
    cache_file.close()
    time.sleep(.05) # to solve cache issue


def make_url_request_using_cache(url, cache, cache_fname):
    '''Check the cache for a saved result for a url.
    If the result is found, return it. Otherwise send a new 
    request, save it, then return it.

    Parameters
    ----------
    url: string
        The URL for the recipe instance
    cache: json dict
        A dictionary of param:value pairs
    
    Returns
    -------
    string
        the results of the request as a Python object loaded from JSON
    '''

    if (url in cache.keys()): # the url is our unique key
        return cache[url]
    else:
        response = requests.get(url, headers=headers)
        cache[url] = response.text 
        save_cache(cache, cache_fname)
        return cache[url] 

def get_recipe_instance(url):
    '''Make an instance from a recipe URL.
    
    Parameters
    ----------
    site_url: string
        The URL for a recipe page in allrecipes.com
    
    Returns
    -------
    instance
        a recipe instance
    '''
    response = requests.get(url, headers=headers) # include headers in the request
    url_text = make_url_request_using_cache(url, CACHE_DICT, CACHE_FILE_NAME) # implement caching; recipes only use the regular cache
    soup = BeautifulSoup(response.text, "html.parser") # convert saved cache data to a BeautifulSoup object
    return Recipe(url_text, soup) # create an instance of a Recipe

def parse_single_from_db(single_from_db):
    '''Parse tuples with single strings from database.
    
    Parameters
    ----------
    single_from_db: list of tuples
        Some recipe element from db
        Single strings inside of tuples
    
    Returns
    -------
    list
        without tuples
    '''
    db_list = []
    for s in single_from_db: # parse tuple recipe names here to reuse -- saves code
        sstring = s[0]
        db_list.append(sstring)
    return db_list

def parse_list_from_db(list_from_db):
    '''Parse tuples with lists from database.
    
    Parameters
    ----------
    list_from_db: list of tuples
        Some recipe element from db
        Tuples contain long string that can
            be separated into a list by ";"    
    Returns
    -------
    list
        without tuples
    '''
    db_new_list = []
    for l in list_from_db: # parse tuple recipe names here to reuse -- saves code
        lstring = l[0].split(";")
        db_new_list.append(lstring)
    return db_new_list

def replace_comma(list_from_db):
    '''Remove commas from numbers in database,
    so that they can be converted to int.
    
    Parameters
    ----------
    list_from_db: list of tuples
        Review or rating number element from db
        Single strings inside of tuples
    
    Returns
    -------
    list
        without tuples and commas
    '''
    # replace commas in lists (e.g. 1,112 --> 1112)
    no_commas = []
    for l in list_from_db:
        if type(1) == type(l[0]): # some have commas, some don't
            l_int = l[0]
        else:
            l_str = l[0].replace(",", "")
            l_int = int(l_str)
        no_commas.append(l_int)
    return no_commas

def nutrition_plot(nutrition_list, recipes_list):
    '''Creates a bar plot using the number of calories 
    for each recipe, saves to an html file, and shows 
    the file. 

    Parameters
    ----------
    nutrition_list: list
        nutritions per serving in each recipe
    recipe_list: list
        names of recipes

    Returns
    -------
    None
    '''
    # parse nutrition_list, already in per serving format
    calorie_list = parse_list_from_db(nutrition_list)

    num_calories = []
    for c in calorie_list:
        calorie = c[0].split()[0]
        num_calories.append(int(calorie))
    
    bar_data = go.Bar(x=recipes_list, y=num_calories)
    basic_layout = go.Layout(title="Recipes by Calories Per Serving", xaxis_title="Recipe", yaxis_title="Calories")
    fig = go.Figure(data=bar_data, layout=basic_layout)
    fig.write_html("plot1.html", auto_open=True)

def ratings_reviews_plot(recipes_list, num_ratings, num_reviews):
    '''Creates a scatter plot using a number of ratings and number of 
    reviews for each recipe, saves to an html file, and shows the file. 

    Parameters
    ----------
    recipe_list: list
        names of recipes
    num_ratings: list
        number of ratings for each recipe
    num_reviews: list
        number of reviews for each recipe

    Returns
    -------
    None
    '''
    num_ratings_2 = replace_comma(num_ratings)
    num_reviews_2 = replace_comma(num_reviews)

    recipes = recipes_list
    ratings = num_ratings_2
    reviews = num_reviews_2

    scatter_data = go.Scatter(
        x=reviews, 
        y=ratings,
        text=recipes, 
        marker={"symbol":"circle", "size":15, "color": "pink"},
        mode="markers", 
        textposition="top center")
    basic_layout = go.Layout(title="Recipes: Ratings vs. Reviews")

    fig = go.Figure(data=scatter_data, layout=basic_layout)
    fig.update_layout(xaxis_title="Number of Reviews", yaxis_title="Number of Ratings")
    fig.write_html("plot2.html", auto_open=True)

def rating_score_plot(recipe_list, num_ratings, num_reviews, rating, num_steps): # from db
    '''Creates a scatter plot using a rating score for each recipe, 
    saves to an html file, and shows the file. 

    Parameters
    ----------
    recipe_list: list
        names of recipes
    num_ratings: list
        number of ratings for each recipe
    num_reviews: list
        number of reviews for each recipe
    rating: list
        average rating out of 5 for each recipe
    num_steps: list
        number of steps for each recipe

    Returns
    -------
    None
    '''
    # Rating score = stars * (number of reviews / number of ratings)
    # Essentially stars * the proportion of people that felt compelled to write reviews 
    # Any trend between "rating score" and number of steps?

    num_ratings_2 = replace_comma(num_ratings) # remove commas from numbers
    num_reviews_2 = replace_comma(num_reviews) # remove commas from numbers
    rating_2 = parse_single_from_db(rating) # remove tuples
    num_steps_2 = parse_single_from_db(num_steps) # remove tuples

    star_rating = []
    for r in rating_2:
        flr = float(r)
        star_rating.append(flr)

    rating_scores = []
    for i in range(len(recipe_list)):
        rating_score = star_rating[i] * (num_reviews_2[i] / num_ratings_2[i]) # calculate "rating score"
        rating_scores.append(rating_score)

    scatter_data = go.Scatter(
        x=rating_scores, 
        y=num_steps_2,
        text=recipe_list, 
        marker={"symbol":"circle", "size":15, "color": "green"},
        mode="markers", 
        textposition="top center")
    basic_layout = go.Layout(title="Recipes: 'Ratings Score' vs. Number of Steps")

    fig = go.Figure(data=scatter_data, layout=basic_layout)
    fig.update_layout(xaxis_title="Rating Score", yaxis_title="Number of Steps", autosize=False, width = 512, height = 512)
    fig.write_html("plot3.html", auto_open=True)

def remove_dupes(dupe): # for ingredient parsing below
    '''Remove duplicates from a list.
    
    Parameters
    ----------
    dupe: list
        the list to remove elements from

    Returns
    -------
    list
        without duplicates
    '''
    no_duplicates = []
    for i in dupe:
        if i not in no_duplicates:
            no_duplicates.append(i)
    return no_duplicates

def ingredients_parsing(master_ingredients_list):
    '''Takes raw ingredients and removes stopwords. Creates ingredients
    that can be used in plots or queried through Kroger API. 

    Parameters
    ----------
    master_ingredients_list: list
        raw ingredients

    Returns
    -------
    list
        ingredients in a friendlier format, without stopwords
    '''
    stopwords = ["teaspoons", "teaspoon", "tablespoons", "tablespoon", "ounces", "ounce", 
    "fluid ounces", "fluid ounce", "gills", "gill", "cups", "cup", "pints", "pint",  "quarts",
    "quart", "gallons", "gallon", "pounds", "pound", "grams", "gram", "packages", "package", 
    "canned", "cans", "can", "inches", "inch", "crumbs", "crumb", "cubes", "cube", "warm", "cold", 
    "hot", "chilled", "refrigerated", "container", "packed", "pack", "finely", "fine", "chopped",
    "instant", "mix", "room temperature", "diced", "sliced", "uncooked", "optional", "mashed",
    "peeled", "bulk", "pureed", "frozen", "ground", "dried", "minced", "cooked", "to", "taste",
    "boxes", "such as", "large", "small", "sheets", "grated", "pinch", "sifted", "lightly", 
    "light", "dark", "medium", "fresh", "jar", "boxed", "coarsely", "rinsed", "bunch", "freshly",
    "as", "needed", "bag", "roughly", "very", "thinly", "thin", "cubed", "piece", "matchsticks",
    "grated", "part", "just", "ripe", "raw"] 
    # stopwords were derived from looking at many recipes

    stopwords_2 = ["(", ")", "."] # punctuation is treated differently

    ingredients_master = []

    for i in range(len(master_ingredients_list)):
        ingredients_single = []
        for block in master_ingredients_list[i]:  # for ingredient long string in ingredient list 
            a = block.split(",")[0]
            b = a.split()

            new_string = ""
            ns = ""
            for c in b: # for word in reduced ingredient string "b"
                c_copy = c.lower() # just in case some ingredients are capitalized

                for m in stopwords_2: # always get rid of punctuation in stopwords2
                    c_copy = c_copy.replace(m, "")

                for m in stopwords: # get rid of words only in complete matches --> so no "can" taken from "pecans"
                    if m == c_copy:
                        c_copy = c_copy.replace(m, "")

                    # c_copy = c_copy.replace(m, "")

                if c_copy.isnumeric() == True:
                    c_copy = ""
                
                if c_copy == "":
                    continue

                new_string += " " + c_copy
                ns = new_string.strip()

            ingredients_single.append(ns)

        ingredients_single = remove_dupes(ingredients_single)
        ingredients_master.append(ingredients_single)
            
    return(ingredients_master)

def allergen_plot(recipe_list, cleaned_ingredients_list):
    '''Creates a stacked bar plot of common allergens in recipes, 
    saves to an html file, and shows the file. 

    Parameters
    ----------
    recipe_list: list
        names of recipes
    cleaned_ingredients_list: list
        ingredients in a friendly format
        
    
    Returns
    -------
    None
    '''
    # allows you to watch out and switch the recipe/make substitutions
    # define strings related to common allergens: 

    dairy = ["butter", "buttermilk", "cream cheese", "cheese", "cottage cheese", "cream", "curds", "ghee", "milk", 
    "sour cream", "whey", "yogurt"]

    egg = ["eggs", "egg"]

    peanut = ["peanuts", "peanut"]

    tree_nut = ["almonds", "almond", "brazil nuts", "brazil nut", "cashews", "cashew", "chestnuts", 
    "chestnut", "filberts", "filbert", "hazelnuts", "hazelnut", "hickory nuts", "hickory nut", 
    "macadamia nuts", "macadamia nut", "pecans", "pecan", "pine nuts", "pine nut", "pistachios", 
    "pistachio", "walnuts", "walnut"]

    dairy_list = []
    egg_list = []
    peanut_list = []
    tree_nut_list = []
    other_list = [] 

    # for each recipe, append allergy-related words to the appropriate lists
    for c in cleaned_ingredients_list:
        c_copy = c
        count_1 = 0
        dairy_recipe = count_1
        for d in dairy:
            if d in c_copy:
                count_1 += 1
        dairy_list.append(count_1)

        count_2 = 0
        egg_recipe = count_2
        for e in egg:
            if e in c_copy:
                count_2 += 1
        egg_list.append(count_2)

        count_3 = 0
        peanut_recipe = count_3
        for p in peanut:
            if p in c_copy:
                count_3 += 1
        peanut_list.append(count_3)

        count_4 = 0
        tree_nut_recipe = count_4
        for t in tree_nut:
            if t in c_copy:
                count_4 += 1 
        tree_nut_list.append(count_4)

        other_count = len(c_copy) - count_1 - count_2 - count_3 - count_4 # ingredients not related to the listed allergens
        other_list.append(other_count)

    # proportions based on number of allergen ingredients in each recipe, not on weight/volume
    x = recipe_list
    fig = go.Figure(go.Bar(x=x, y=dairy_list, name="Dairy"))
    fig.add_trace(go.Bar(x=x, y=egg_list, name="Egg"))
    fig.add_trace(go.Bar(x=x, y=peanut_list, name="Peanut"))
    fig.add_trace(go.Bar(x=x, y=tree_nut_list, name="Tree Nut"))
    fig.add_trace(go.Bar(x=x, y=other_list, name="Other Ingredients"))

    fig.update_layout(barmode="stack", title="Common Allergens in Recipes", xaxis_title="Recipe", yaxis_title="Number of Ingredients", autosize=False, width = 800, height = 400)
    fig.update_xaxes(categoryorder="category ascending")
    fig.write_html("plot4.html", auto_open=True)

def review_plot(review_list):
    '''Creates a wordcloud of top reviews, saves to
    a png file, and shows the file. 

    Parameters
    ----------
    review_list: list
        top reviews
    
    Returns
    -------
    None
    '''
    # first page reviews are list as most helpful; javascript is hiding reviews on other pages
    # parse review list for single words

    review_list_2 = parse_list_from_db(review_list) # without the tuples, top helpful reviews

    transient_list = []
    for block in review_list_2[0]: 
        b = block.split()
        transient_list.append(b)
    fixed_list = [x for i in transient_list for x in i] # list comprehension

    # lowercase    
    for i in range(len(fixed_list)):
        fixed_list[i] = fixed_list[i].lower()

    # take out stopwords from fixed_list using gensim package
    words = fixed_list.copy()
    words_2 = []
    for word in words:  # iterating on a copy since removing will mess things up
        w = word.strip(punctuation)
        r = remove_stopwords(w)
        words_2.append(r)

    # word cloud
    plt.subplots(figsize = (8,8))
    wordcloud = WordCloud(background_color = "white", max_words = 100, width = 512, height = 512).generate(' '.join(words_2))
    plt.imshow(wordcloud, interpolation = "bilinear")
    plt.axis("off")
    plt.savefig("plot5.png")
    plt.show()

def construct_unique_key(baseurl, params):
    '''Constructs a key that is guaranteed to uniquely and 
    repeatably identify an API request by its baseurl and params.

    Parameters
    ----------
    baseurl: string
        The URL for the API endpoint
    params: dict
        A dictionary of param:value pairs
    
    Returns
    -------
    string
        the unique key as a string
    '''
    param_strings = []
    for k in params.keys():
        param_strings.append("{}={}".format(k, params[k]))
    param_strings.sort()
    unique_key = baseurl + "?" + "&".join(param_strings)
    return unique_key

def token_saver(token):
    '''Save an authorization token to secret cache.

    Parameters
    ----------
    token: dict
        OAuth2Token fetched during auth

    Returns
    -------
    None
    '''
    CACHE_DICT_S["token"] = token
    with open(CACHE_FILE_S, "w") as outfile:
        outfile.write(json.dumps(CACHE_DICT_S, indent=2))
    outfile.close()

def get_kroger_auth(parsed_ingredient_list):
    '''Authenticate using OAuth2 and add recipe ingredients to 
    Kroger cart.

    Parameters
    ----------
    parsed_ingredient_list: list
        ingredients in a friendly format to be passed to cart
    
    Returns
    -------
    string
        the results of the request as a Python object loaded from JSON
    '''
    CACHE_DICT_S = load_cache(CACHE_FILE_S) # did not load in main

    krog_token_url = "https://api.kroger.com/v1/connect/oauth2/token"
    krog_auth_url = "https://api.kroger.com/v1/connect/oauth2/authorize"

    client_key = secrets.KROGER_CLIENT_ID
    client_secret = secrets.KROGER_CLIENT_SECRET
    redirect = secrets.REDIRECT_URI

    scopes = ["profile.compact", "product.compact", "cart.basic:write"]
    extra = {"client_id": client_key, "client_secret": client_secret}

    if "token" in CACHE_DICT_S.keys():
        token = CACHE_DICT_S["token"]
        oauth = OAuth2Session(client_id=client_key, token=token, auto_refresh_url=krog_token_url, auto_refresh_kwargs=extra, token_updater=token_saver)

    ### create refreshable token and save it to cache ###
    else:
        oauth = OAuth2Session(client_id=client_key, redirect_uri=redirect, scope=scopes)
        authorization_url, state = oauth.authorization_url(krog_auth_url)

        flag_launch = True
        while flag_launch == True:
            launch = input("Enter launch (L) to launch authentication in a browser -- or exit (E) to exit the program: ").lower() # create a message about launching the url
            if launch == "exit" or launch == "e":
                print("Goodbye")
                sys.exit()
            
            elif launch == "launch" or launch == "l":
                flag_launch = False # break out of loop
                break

            elif launch != "exit" and launch != "e" and launch != "launch" and launch != "l":
                print("[Error] Please enter valid input launch (L) or exit (E)")

        webbrowser.open(authorization_url, new=2, autoraise=True)
        
        print()
        callback = input("Please paste the full callback URL from the browser: ") # user will enter full redirect URI
        token = oauth.fetch_token(krog_token_url, authorization_response=callback, client_secret=client_secret) # get token
        token["expires_in"] = -300 # needs to be negative for refresh
        token_saver(token) # does saving below, defined in function to pass to token refresher

    ### product information from kroger ###
    baseurl = "https://api.kroger.com/v1/products"
    params = {}
    params["filter.limit"] = 1 # only show one item
    responses = []

    for product in parsed_ingredient_list:
        params["filter.term"] = product
        request_key = construct_unique_key(baseurl, params)

        if request_key in CACHE_DICT_K.keys():
            response = CACHE_DICT_K[request_key]
        
        else:
            new_response = oauth.get(request_key)
            CACHE_DICT_K[request_key] = new_response.json()
            with open(CACHE_FILE_K, "w") as outfile:
                outfile.write(json.dumps(CACHE_DICT_K, indent=2))
            outfile.close()
            response = CACHE_DICT_K[request_key]

        responses.append(response)

    ### to add to the cart
    baseurl_2 = "https://api.kroger.com/v1/cart/add"
    items_dict = {}
    list_qu = []

    for i in range(len(responses)):
        r = responses[i]
        r_prod = parsed_ingredient_list[i]

        try: 
            if len(r["data"]) == 0: 
                print(r_prod.capitalize(), "could not be added to cart") # option in case a search item is not found
                continue
        except: #KeyError: if the search term is greater than 8, it will trigger an error
            print(r_prod.capitalize(), "could not be added to cart") # option in case a search item is not found
            continue

        # specific format required by Kroger API
        if len(r["data"]) > 0:
            qu = {}
            qu["upc"] = r["data"][0]["upc"]
            qu["quantity"] = 1
            list_qu.append(qu)
        
    items_dict["items"] = list_qu
    oauth.put(url=baseurl_2, json=items_dict, headers={'Content-Type': 'application/json'}) # add items dict to the cart 

    return responses

##########################
#########  MAIN ##########
##########################

if __name__ == "__main__":
    # Load the cache, save in global variable
    CACHE_DICT = load_cache(CACHE_FILE_NAME)
    CACHE_DICT_K = load_cache(CACHE_FILE_K)
    
    create_tables()

    ######### INTERACTIVE #########
    flag = True # set flag
    flag_a = True # set flag
    flag_c = False # set flag
    flag_d = False # set flag
    flag_e = False # set flag
    flag_f = False # set flag

    while flag == True:
        while flag_a == True: 
            print()
            recipe_query = input("Enter a recipe query (e.g. cake, pasta, burrito) or \"exit\": ").lower() # force to lower case
            print()

            if recipe_query == "exit":
                print("Goodbye!")
                sys.exit()
                
            else:
                # build recipe instances from recipe query
                recipe_dict = build_recipe_url_dict() 

                recipe_instances = []
                for recipe_url in recipe_dict[recipe_query]:
                    ins = get_recipe_instance(recipe_url)
                    recipe_instances.append(ins)

                print("~-" * 37)
                print("List of", recipe_query.capitalize(), "Recipes (by popularity)") # force all to capitalize for aesthetics 
                print("~-" * 37)

                count = 1 # set count for list

                if len(recipe_instances) == 0:
                    print("No recipes related to query")
                    continue

                for recipe in recipe_instances[:20]: # only show 20 recipes
                    print("[" + str(count) + "] " + recipe.info())
                
                    ######### DATABASE PT 1 #########
                    ### add recipe info to the database
                    rec_list = []
                    rec_list.append(str(recipe.name))
                    rec_list.append(recipe_query)
                    rec_list.append(recipe_dict[recipe_query][count-1]) # urls from recipe_dict
                    rec_list.append(int(recipe.num_steps))

                    # directions edge case
                    directions_str = "" # create a list so the string doesn't get weird going/coming from the db
                    if recipe.directions == "No Directions":
                         directions_str += str(recipe.directions) + "; "
                    else:
                        for d in recipe.directions:
                            directions_str += str(d) + "; " # so that I can split the lists by ";" later
                    directions_str = directions_str[:-2] # to get rid of the last "; "
                    rec_list.append(directions_str) 
                        
                    rec_list.append(str(recipe.rating))
                    rec_list.append(str(recipe.num_rating))
                    add_to_recipe_table(rec_list) # creates a table in database

                    ### add ingredient info to the database
                    ingr_list = []
                    ingr_list.append(str(recipe.name))
                    ingr_list.append(recipe_query)

                    ingredients_str = "" # create a list so the string doesn't get weird going/coming from the db
                    for i in recipe.ingredients:
                        ingredients_str += str(i) + "; " # so that I can split the lists by ";" later
                    ingredients_str = ingredients_str[:-2] # to get rid of the last "; "
                    ingr_list.append(ingredients_str)

                    ingr_list.append(int(recipe.servings))

                    # nutrition edge case
                    nutrition_str = "" # create a list so the string doesn't get weird going/coming from the db
                    if recipe.nutrition == "No nutrition information":
                         nutrition_str += str(recipe.nutrition) + "; "
                    else:
                        for n in recipe.nutrition:
                            nutrition_str += str(n) + "; " # so that I can split the lists by ";" later
                    nutrition_str = nutrition_str[:-2] # to get rid of the last "; "
                    ingr_list.append(nutrition_str) 

                    add_to_ingredients_table(ingr_list) # creates a table in database

                    ### add review info to the database
                    rev_list = []
                    rev_list.append(str(recipe.name))
                    rev_list.append(recipe_query)

                    # review edge case
                    review_str = "" # create a list so the string doesn't get weird going/coming from the db
                    if recipe.review == "No reviews":
                         review_str += str(recipe.review) + "; "
                    else:
                        for r in recipe.review:
                            review_str += str(r) + "; " # so that I can split the lists by ";" later
                    review_str = review_str[:-2] # to get rid of the last "; "
                    rev_list.append(review_str) 

                    rev_list.append(str(recipe.num_review))
                    add_to_reviews_table(rev_list) # creates a table in database

                    count += 1

                flag_a = False # input is valid
                flag_c = True # set flag

        ######### INGREDIENTS #########
        while flag_c == True: 
            print()
            choice = input("Choose a recipe number for detailed ingredients or exit (E) or back (B): ")
            print()

            if choice.isnumeric() == False: 
                if choice == "e" or choice == "exit": # flexible options
                    print()
                    print("Goodbye!")
                    sys.exit()
                
                elif choice == "b" or choice == "back":
                    flag_c = False # break out of the loop
                    flag_a = True # do main first input again
                    break

                else:
                    print()
                    print("[Error] You must choose a number or exit (E) or back (B)")

            if choice.isnumeric() == True: 
                if int(choice) >= count:
                    print()
                    print("[Error] Choose a number within the list range")

                else:
                    recipe_name = recipe_instances[:20][int(choice)-1]
                    ingr = recipe_name.ingredients
                    
                    print("~-" * 37)
                    print("Ingredients for", str(recipe_name.name)) # make sure this is the site that corresponds to the number 
                    print("~-" * 37)
                    
                    counter = 1 # set count
                    for i in ingr:
                        print("[" + str(counter) + "] " + str(i))
                        counter += 1
                    
                    flag_c = False # moves on from this section
                    flag_d = True # moves on to cart part

        ######### CART #########
        while flag_d == True: 
            print()
            print("Would you like to add the recipe ingredients to a Kroger cart?")
            cart_choice = input("Enter yes (Y), back (B), continue to plots (C), or exit (E): ").lower() # force to lower case  
            print()

            if cart_choice == "e" or cart_choice == "exit":
                print()
                print("Goodbye!")
                sys.exit()
            
            elif cart_choice == "b" or cart_choice == "back": 
                flag_d = False # break out of the loop
                flag_c = True # moves back to ingredients section
                break   

            elif cart_choice == "c" or cart_choice == "continue to plots": # to continue on 
                flag_d = False # break out of loop
                flag_e = False # move on to plots
                flag_f = True # avoid asking question about plots twice, go to plot choices

            elif cart_choice!= "e" and cart_choice != "exit" and cart_choice != "b" and cart_choice != "back" and cart_choice != "c" and cart_choice != "continue to plots" and cart_choice != "y" and cart_choice != "yes":
                print("[Error] You must enter yes (Y), back (B), continue to plots (C), or exit (E)")

            elif cart_choice == "yes" or cart_choice == "y":
                cart_list_owned = [] # make a list of every item that the user already has
                cart_list = [] # make a list of every item that the user needs

                print("~-" * 37)
                print("Creating a Cart List for", str(recipe_name.name)) # make sure this is the site that corresponds to the number 
                print("~-" * 37)

                for i in ingr:
                    cart_flag = True # local flag for loop
                    while cart_flag == True: 
                        cart_check = input("Do you have " + str(i) + "? (Y/N): ").lower() # force to lower case
                    
                        if cart_check != "n" and cart_check != "y":
                            print("[Error] You must choose \"Y\" or \"N\"")
                            continue

                        if cart_check == "y":
                            cart_list_owned.append(i)
                            cart_flag = False

                        if cart_check == "n":
                            cart_list.append(i)
                            cart_flag = False
                
                parsed_cart_list = ingredients_parsing([cart_list]) # parse cart_list for "usable" search terms --> flour instead of 2 cups flour
            
                ######### KROGER API #########
                print()
                print("You will have to log in to Kroger during authentication")
                print("Create a new Kroger account at https://www.kroger.com/account/create?redirectUrl=/ \nIf you don't want to use your main account to test the program")
                print()

                # authorizes, finds product upcs, passes to cart
                kroger_products = get_kroger_auth(parsed_cart_list[0])

                print()
                print("Success! Your items have been added.")

                for kp in range(len(kroger_products)):
                    k = kroger_products[kp]
                    p  = parsed_cart_list[0][kp]
                    product = Product(json=k)
                    shop_list = []

                    ######### DATABASE PT 2 #########
                    # Kroger related items
                    shop_list.append(str(product.upc))
                    shop_list.append(p)
                    shop_list.append(str(ingr))
                    shop_list.append(str(product.brand))
                    shop_list.append(str(product.categories))
                    shop_list.append(str(product.description))
                    shop_list.append(product.limit)
                    add_to_cart_list_table(shop_list) # creates a table in database

                return_flag_x = True
                while return_flag_x == True:
                    print()
                    print("Would you like to view your cart?")
                    cart_view = input("Enter yes (Y), back to recipes (B), continue to plots (C), or exit (E): ").lower() # force to lower case
                    
                    if cart_view == "exit" or cart_view == "e":
                        print()
                        print("Goodbye!")
                        sys.exit()

                    if cart_view != "continue to plots" and cart_view != "c" and cart_view != "yes" and cart_view != "y" and cart_view != "exit" and cart_view != "e" and cart_view != "back to recipes" and cart_view != "b":
                        print("[Error] You must choose yes (Y), continue to plots (C), or exit (E)")
                        continue

                    if cart_view == "back to recipes" or cart_view == "b":
                        print("Ok, everything should be in your cart!")
                        print()

                        # refresh the user of the options here; not part of the ingredients loop -- in the previous section
                        print("~-" * 37)
                        print("List of", recipe_query.capitalize(), "Recipes (by popularity)") # force all to capitalize for aesthetics 
                        print("~-" * 37)

                        count_new = 1
                        for recipe in recipe_instances[:20]: # only show 20 recipes
                            print("[" + str(count_new) + "] " + recipe.info())
                            count_new += 1

                        return_flag_x = False # break from this loop
                        flag_d = False # break from cart loop, just in case
                        flag_c = True # move back to recipe list choice
                        break 

                    if cart_view == "continue to plots" or cart_view == "c":
                        print("Ok, everything should be in your cart!")
                        return_flag_x = False # break from this loop
                        flag_d = False # break from cart loop, just in case
                        flag_e = True # move on to plots

                    if cart_view == "yes" or cart_view == "y":
                        webbrowser.open("https://www.kroger.com/cart", new=2, autoraise=True) # view your cart in a browser
                        flag_d = False # break from cart loop, just in case
                        flag_e = True # move on to plots

        ######### PLOTS #########
        while flag_e == True: 
            print()
            print("Would you like to view recipe-related plots?")
            plot_choice = input("Enter yes (y), back (B), or exit (E): ").lower() # force to lower case
            print()

            if plot_choice == "exit" or plot_choice == "e":
                print()
                print("Goodbye!")
                sys.exit()

            elif plot_choice == "back" or plot_choice == "b":
                flag_e = False # break out of the loop
                flag_d = True # go to cart
                break  

            elif plot_choice != "exit" and plot_choice != "e" and plot_choice != "back" and plot_choice != "b" and plot_choice != "yes" and plot_choice != "y":
                print("[Error] You must choose \"yes,\" \"back,\" or \"exit\"")

            elif plot_choice == "yes" or plot_choice == "y":
                flag_f = True # go to plot choices
                flag_e = False # break from this loop
            
        while flag_f == True:
            print("~-" * 37)
            print("What kind of plot would you like to view?")
            print("~-" * 37)

            print("[1] Nutrition Information (all recipes in query)")
            print("[2] Ratings vs. Reviews Numbers (all recipes in query)")
            print("[3] Number of Steps in Recipe by Rating Score (all recipes in query)")
            print("[4] Allergen Information (all recipes in query)")
            print("[5] Common Words in Reviews (previously chosen recipe)")

            return_flag_2 = True
            while return_flag_2 == True:
                print()
                plot_num = input("Enter a plot number: ") 
                if plot_num.isnumeric() == False: 
                    print()
                    print("Please enter a number")

                elif plot_num.isnumeric() == True:
                    # define recipe name list here here because multiple plots need it
                    query_r = "SELECT recipe_name FROM recipes WHERE query =" + "\"" + recipe_query + "\"" 
                    qr = pull_from_db(query_r) # recipes in tuple format
                    qr_recipes_list = parse_single_from_db(qr) # turn recipes into a list

                    query_nra = "SELECT total_number_ratings FROM recipes WHERE query =" + "\"" + recipe_query + "\""
                    qnra = pull_from_db(query_nra) # number of ratings in tuple format

                    query_nre = "SELECT total_number_reviews FROM reviews WHERE query =" + "\"" + recipe_query + "\""
                    qnre = pull_from_db(query_nre) # number of reviews in tuple format

                    if int(plot_num) > 5: # only 5 options
                        print("[Error] Choose a number within the list range")
                    
                    ######### PLOT 1 #########
                    elif int(plot_num) == 1:
                        query_nps = "SELECT nutrition_per_serving FROM ingredients WHERE query =" + "\"" + recipe_query + "\""
                        qnps = pull_from_db(query_nps) # nutrition per serving in tuple format
                        nutrition_plot(qnps, qr_recipes_list) # send to nutrition plot function

                        return_flag_2 = False # break from this loop so we don't get stuck in plots
                        flag_e = True # break from plot choice loop
                        flag_f = False # return to main plot loop

                    ######### PLOT 2 #########
                    elif int(plot_num) == 2:
                        ratings_reviews_plot(qr_recipes_list, qnra, qnre)

                        return_flag_2 = False # break from this loop so we don't get stuck in plots
                        flag_e = True # break from plot choice loop
                        flag_f = False # return to main plot loop

                    ######### PLOT 3 #########
                    elif int(plot_num) == 3:
                        query_r5 = "SELECT rating_out_of_5 FROM recipes WHERE query =" + "\"" + recipe_query + "\""
                        query_ns = "SELECT number_of_steps FROM recipes WHERE query =" + "\"" + recipe_query + "\""

                        qr5 = pull_from_db(query_r5) # rating in tuple format
                        qns = pull_from_db(query_ns) # number of steps in tuple format
                        
                        rating_score_plot(qr_recipes_list, qnra, qnre, qr5, qns)

                        return_flag_2 = False # break from this loop so we don't get stuck in plots
                        flag_e = True # break from plot choice loop
                        flag_f = False # return to main plot loop

                    ######### PLOT 4 #########
                    elif int(plot_num) == 4:
                        query_i = "SELECT ingredients FROM ingredients WHERE query =" + "\"" + recipe_query + "\""
                        qi = pull_from_db(query_i) # rating in tuple format

                        better_qi_list = parse_list_from_db(qi) # without the tuples
                        cleaned_list = ingredients_parsing(better_qi_list) # feed output to allergen plot function
                        allergen_plot(qr_recipes_list, cleaned_list)
                        
                        return_flag_2 = False # break from this loop so we don't get stuck in plots
                        flag_e = True # break from plot choice loop
                        flag_f = False # return to main plot loop

                    ######### PLOT 5 #########
                    elif int(plot_num) == 5:
                        query_rev = "SELECT top_reviews FROM reviews WHERE recipe =" + "\"" + str(recipe_name.name) + "\"" # only the selected recipe
                        qrev = pull_from_db(query_rev) # rating in tuple format

                        review_plot(qrev) # exclude first two because they're "highlighted" and might appear more than once
                        
                        return_flag_2 = False # break from this loop so we don't get stuck in plots
                        flag_e = True # break from plot choice loop
                        flag_f = False # return to main plot loop