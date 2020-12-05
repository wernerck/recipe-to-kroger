#################################
##### Name: Christian Werner ####
##### Uniqname: wernerck     ####
#################################

import bs4
from bs4 import BeautifulSoup
from string import punctuation, digits 
import requests
from gensim.parsing.preprocessing import remove_stopwords
import json
import sqlite3
import plotly
import plotly.graph_objects as go
import chart_studio.plotly as py
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import secrets # file that contains API keys
import sys

from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from requests.auth import HTTPBasicAuth

import webbrowser


# Request headers
headers = {
    'User-Agent': 'UMSI 507 Course Project - Python Scraping',
    'From': 'wernerck@umich.edu',
    'Course-Info': 'https://si.umich.edu/programs/courses/507'
}

# API from secrets file
client_key = secrets.KROGER_CLIENT_ID
client_secret = secrets.KROGER_CLIENT_SECRET
redirect = secrets.REDIRECT_URI

# CACHE
CACHE_FILE_NAME = 'cache.json'
CACHE_DICT = {}

class Recipe:
    '''a recipe

    Instance Attributes
    -------------------
    category: string
        the category of a recipe (e.g. 'cake')
    
    name: string
        the name of a recipe (e.g. 'Chocolate Cake')

    rating: string
        the rating of a recipe (e.g. '93% would make again', '')
        some ratings are blank
    
    ingredients: string
        the ingredients of a recipe (e.g. 'flour', 'water', ...)
    
    nutrition: string
        the nutritional information of a recipe (e.g. 'Calories 409', ...)
    '''
    # Class constants to parse HTML
    NAME_DIV_CLASS = 'headline-wrapper'
    NAME_CONTAINER_TAG = 'h1'
    RATING_DIV_CLASS = 'recipe-review-container euDisabled'
    RATING_DIV_CONTAINER = 'span'
    NUMRAT_DIV_CLASS = 'partial ugc-ratings'
    NUMRAT_DIV_CONTAINER = 'span'    
    REVIEW_DIV_CLASS = 'recipes-reviews-container container'
    REVIEW_DIV_CONTAINER = 'span'
    NUMREV_DIV_CLASS = 'partial ugc-ratings'
    NUMREV_DIV_CONTAINER = 'a'     
    SERV_DIV_CLASS = 'recipe-meta-item-body'
    INGREDIENTS_DIV_CLASS = 'recipe-shopper-wrapper'
    INGREDIENTS_CONTAINER_TAG = 'span'
    NUTRITION_DIV_CLASS = 'nutrition-section container'
    NUTRITION_CONTAINER_TAG = 'div'    

    def __init__(self, url, details_soup):
        self.url = url
        self.name = self.extract_name(details_soup)
        self.rating = self.extract_rating(details_soup)
        self.num_rating = self.extract_num_rating(details_soup)
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
            .find(self.RATING_DIV_CONTAINER, class_='review-star-text')
            .string
            .strip()
            .split(":")[1])
            return rat 
        except:
            return "No rating"

    def extract_num_rating(self, soup):
        try: # use try/catch in case missing
            nrat = (soup.find(class_=self.NUMRAT_DIV_CLASS)) #
            nums = []
            nums_2 = []
            for n in nrat.find_all(self.NUMRAT_DIV_CONTAINER, class_='ugc-ratings-item'):
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

    def extract_review(self, soup): # from the first page
        try: # use try/catch in case review is missing
            rev = (soup.find(class_=self.REVIEW_DIV_CLASS))
            revs = []
            for n in rev.find_all(self.REVIEW_DIV_CONTAINER, class_='recipe-review-body--truncated'):
                nstr = n.string
                nbrack = nstr.split('\n')
                good = nbrack[3].strip()
                revs.append(good)
            # print(revs)
            return revs
        except:
            return "No reviews"

    def extract_num_review(self, soup):
        try: # use try/catch in case missing
            nrev = (soup.find(class_=self.NUMREV_DIV_CLASS)) #
            nums = []
            nums_2 = []
            for n in nrev.find_all(self.NUMREV_DIV_CONTAINER, class_='ugc-ratings-link ugc-reviews-link'):
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
        return serving[0] #list with 1 number, the serving for this recipie

    def extract_ingredients(self, soup):
        ing = (soup.find(class_=self.INGREDIENTS_DIV_CLASS)
        .find_all(self.INGREDIENTS_CONTAINER_TAG, class_='ingredients-item-name'))
        ingrs = []
        for i in ing:
            ingrs.append(i.string.strip())
        return ingrs

    def extract_nutrition(self, soup):
        try: # use try/catch in case a recipe is missing nutritional info
            nut = (soup.find(class_=self.NUTRITION_DIV_CLASS))
            for n in nut.find_all(self.NUTRITION_CONTAINER_TAG, class_="section-body"):
                nstr = str(n)
                nbrack = nstr.split('\n')
                good = nbrack[1].strip()
                goods = good.split(';')
                
                for i in range(len(goods)):
                    goods[i] = goods[i].strip().capitalize()
                    if i == len(goods) - 1:
                        goods[i] = goods[i][:-1]
            return goods
        except:
            return "No nutrition information"

    def info(self): # info.self() to be displayed in interactive search
        return str(self.name) + ": " + str(self.rating)
    
def create_tables():
    conn = sqlite3.connect("recipe.sqlite")
    cur = conn.cursor()

    create_recipes = '''
        CREATE TABLE IF NOT EXISTS "recipes" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
            "query" TEXT NOT NULL,
            "recipe_name" TEXT NOT NULL,
            "rating" TEXT NOT NULL,
            "total_number_ratings" INTEGER NOT NULL
        );
    '''

    create_ingredients = '''
        CREATE TABLE IF NOT EXISTS "ingredients" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
            "recipe" TEXT NOT NULL,
            "ingredients" TEXT NOT NULL,
            "servings" INTEGER NOT NULL, 
            "nutrition_per_serving" TEXT NOT NULL,
            FOREIGN KEY (recipe) REFERENCES recipes (recipe_name)
        );
    '''

    create_reviews = '''
        CREATE TABLE IF NOT EXISTS "reviews" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
            "recipe"  TEXT NOT NULL,
            "top_reviews" TEXT NOT NULL,
            "total_number_reviews" INTEGER NOT NULL, 
            FOREIGN KEY (recipe) REFERENCES recipes (recipe_name)
        );
    '''

    cur.execute(create_recipes)
    cur.execute(create_ingredients)
    cur.execute(create_reviews)
    conn.commit()

def add_to_recipe_table(recipe_data_list):
    '''
    '''
    conn = sqlite3.connect("recipe.sqlite")
    cur = conn.cursor()
    insert_recipes = '''
        INSERT INTO recipes
        VALUES (NULL, ?, ?, ?, ?);
    '''
    cur.execute(insert_recipes, recipe_data_list)
    conn.commit()

def add_to_ingredients_table(ingredients_data_list):
    '''
    '''
    conn = sqlite3.connect("recipe.sqlite")
    cur = conn.cursor()
    insert_ingredients = '''
        INSERT INTO ingredients
        VALUES (NULL, ?, ?, ?, ?);
    '''
    cur.execute(insert_ingredients, ingredients_data_list)
    conn.commit()

def add_to_reviews_table(reviews_data_list):
    '''
    '''
    conn = sqlite3.connect("recipe.sqlite")
    cur = conn.cursor()
    insert_ingredients = '''
        INSERT INTO reviews
        VALUES (NULL, ?, ?, ?);
    '''
    cur.execute(insert_ingredients, reviews_data_list)
    conn.commit()

def search_for_repeat():
    '''
    '''
    conn = sqlite3.connect("recipe.sqlite")
    cur = conn.cursor()
    query = '''
      SELECT query
      FROM recipes
    '''
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
        e.g. {'cake': ['', ...}
    '''
    BASE_URL = 'https://www.allrecipes.com/search/results/' 

    # queries > 1 word are treated differently 
    # after the first word append "%20" to the beginning of each word
    
    special = "%20"
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
    params["sort"] = 'p' # sort by popular

    param_strings = []
    for k in params:
        param_strings.append("{}={}".format(k, params[k]))
    recipe_page_url = BASE_URL + "?" + "&".join(param_strings)

    # BeautifulSoup parsing
    response = requests.get(recipe_page_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    recipes = {}
    
    recipes_query_list = []
    recipe_list_parent = soup.find_all('div', id='searchResultsApp') # to parse recipe list for crawling
    for tag in recipe_list_parent:
        for recipe_link_parent_tag in tag.find_all('article', class_="fixed-recipe-card"):
            recipe_link_tag = recipe_link_parent_tag.find('div', class_="fixed-recipe-card__info")
            for t in recipe_link_tag:
                recipe_link = t.find('a')
                if type(recipe_link) == bs4.element.Tag:
                    linkdata=recipe_link.get('href')
                    if linkdata[:34] == 'https://www.allrecipes.com/recipe/':
                        recipes_query_list.append(linkdata)
    recipes[recipe_query] = recipes_query_list      
    return recipes

### CACHING ###
def load_cache():
    try:
        cache_file = open(CACHE_FILE_NAME, 'r')
        cache_file_contents = cache_file.read()
        cache = json.loads(cache_file_contents)
        cache_file.close()
    except:
        cache = {}
    return cache

def save_cache(cache):
    CACHE_FILE_NAME = 'cache.json'
    cache_file = open(CACHE_FILE_NAME, 'w')
    contents_to_write = json.dumps(cache)
    cache_file.write(contents_to_write)
    cache_file.close()

def make_url_request_using_cache(url, cache):
    if (url in cache.keys()): 
        # print("Using cache")
        return cache[url]
    else:
        # print("Fetching")
        response = requests.get(url, headers=headers)
        cache[url] = response.text 
        save_cache(cache)
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
    url_text = make_url_request_using_cache(url, CACHE_DICT) # implement caching
    soup = BeautifulSoup(response.text, 'html.parser')
    return Recipe(url_text, soup) # create an instance of a Recipe

def remove_dupes(dupe):
    '''
    '''
    no_duplicates = []
    for i in dupe:
        if i not in no_duplicates:
            no_duplicates.append(i)
    return no_duplicates

def nutrition_plot(recipe_list, nutrition_list):
    '''
    '''
    # parse nutrition_list for calorie information
    # calories per serving?
    # divide by serving info

    calorie_list = []
    for n in nutrition_list:
        calorie = n.split("\'")[1].split()[0]
        calorie_list.append(int(calorie))


    bar_data = go.Bar(x=recipe_list, y=cals_per_serv)
    basic_layout = go.Layout(title="Recipes by Calories Per Serving")
    fig = go.Figure(data=bar_data, layout=basic_layout)
    fig.show()

def ratings_reviews_plot(recipe_list, num_ratings, num_reviews):
    '''
    '''
    # replace commas in lists (e.g. 1,112 --> 1112)

    num_ratings_2 = []
    for nr in num_ratings:
        nr_int = int(nr.replace(",", ""))
        num_ratings_2.append(nr_int)

    num_reviews_2 = []
    for nre in num_reviews:
        nre_int = int(nre.replace(",", ""))
        num_reviews_2.append(nre_int)


    recipes = recipe_list
    reviews = num_reviews_2
    ratings = num_ratings_2

    scatter_data = go.Scatter(
        x=reviews, 
        y=ratings,
        text=recipes, 
        marker={'symbol':'circle', 'size':25, 'color': 'pink'},
        mode='markers', 
        textposition="top center")
    basic_layout = go.Layout(title="Recipes: Ratings vs. Reviews")

    fig = go.Figure(data=scatter_data, layout=basic_layout)
    fig.update_layout(xaxis_title="Number of Reviews", yaxis_title="Number of Ratings")
    fig.write_html("poparea.html", auto_open=True)


def ingredients_parsing(master_ingredients_list):
    '''
    '''
    stopwords = ["teaspoons", "teaspoon", "tablespoons", "tablespoon", "ounces", "ounce", 
    "fluid ounces", "fluid ounce", "gills", "gill", "cups", "cup", "pints", "pint",  "quarts",
    "quart", "gallons", "gallon", "pounds", "pound", "grams", "gram", "packages", "package", 
    "cans", "can", "inches", "inch", "crumbs", "crumb", "cubes", "cube", "warm", "cold", 
    "hot", "chilled", "refrigerated", "container", "(", ")", "."] # add plural first
    # might need to add water

    ingredients_master = []

    for i in range(len(master_ingredients_list)):
        ingredients_single = []
        for block in master_ingredients_list[i]:  #for ingredient long string in ingredient list (i/10)
            a = block.split(",")[0]
            b = a.split()

            new_string = ""
            ns = ""
            for c in b: #for word (sep by space) in reduced ingredient string "b"
                c_copy = c

                for m in stopwords:
                    c_copy = c_copy.replace(m, "")

                if c_copy.isnumeric() == True:
                    c_copy = ""
                
                # try: 
                #     float(c_copy)
                #     c_copy = ""
                # except:
                #     ValueError
                #     continue

                if c_copy == "":
                    continue

                new_string += " " + c_copy
                ns = new_string.strip()

            ingredients_single.append(ns)

        ingredients_single = remove_dupes(ingredients_single)
        ingredients_master.append(ingredients_single)
            
    return(ingredients_master)

def allergen_plot(recipe_list, cleaned_ingredients_list):
    '''
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

        other_count = len(c_copy) - count_1 - count_2 - count_3 - count_4
        other_list.append(other_count)

    # proportions based on number, not on weight/volume
    x = recipe_list
    fig = go.Figure(go.Bar(x=x, y=dairy_list, name='Dairy'))
    fig.add_trace(go.Bar(x=x, y=egg_list, name='Egg'))
    fig.add_trace(go.Bar(x=x, y=peanut_list, name='Peanut'))
    fig.add_trace(go.Bar(x=x, y=tree_nut_list, name='Tree Nut'))
    fig.add_trace(go.Bar(x=x, y=other_list, name='Other Ingredients'))

    fig.update_layout(barmode='stack', title="Common Allergens in Recipes", xaxis_title="Recipe", yaxis_title="Number of Ingredients")
    fig.update_xaxes(categoryorder='category ascending')
    fig.write_html("allergens.html", auto_open=True)

def review_plot(review_list):
    '''
    '''
    # first page reviews most helpful and javascript is hiding reviews on other pages
    # parse review list for single words
    transient_list = []
    for block in review_list[0]: 
        b = block.split()
        transient_list.append(b)
    fixed_list = [x for i in transient_list for x in i] # list comprehension

    # lowercase    
    for i in range(len(fixed_list)):
        fixed_list[i] = fixed_list[i].lower()

    # take out stopwords from fixed_list
    # use gensim.parsing.preprocessing package
    words = fixed_list.copy()
    words_2 = []
    for word in words:  # iterating on a copy since removing will mess things up
        w = word.strip(punctuation)
        r = remove_stopwords(w)
        words_2.append(r)

    # word cloud
    plt.subplots(figsize = (8,8))
    wordcloud = WordCloud(background_color = 'white', max_words = 100, width = 512, height = 512).generate(' '.join(words_2))
    plt.imshow(wordcloud, interpolation = "bilinear")
    plt.axis('off')
    plt.savefig('Recipe-World-Cloud.png')
    plt.show()

def kroger_test():
    '''Obtain API data from Kroger API
    
    Parameters
    ----------
    recipe_object: object
        an instance of a recipe
    
    Returns
    -------
    dict
        a converted API return from Kroger API
    '''
    # Authorization: Basic {{base64(secrets.KROGER_CLIENT_ID:secrets.KROGER_CLIENT_SECRET)}}
    # Authorization URL: https://api.kroger.com/v1/connect/oauth2/authorize
    # token_url = 'https://api.kroger.com/v1/connect/oauth2/token'
    # krog_auth_url = 'https://api.kroger.com/v1/connect/oauth2/authorize'


    # # Customer Context - Cart
    # auth_url: 'https://api.kroger.com/v1/connect/oauth2/authorize'
    token_url = 'https://api.kroger.com/v1/connect/oauth2/token'
    auth = HTTPBasicAuth(client_key, client_secret)
    client = BackendApplicationClient(client_id=client_key)
    # scopes = ['cart.basic:write', 'product.compact']
    oauth = OAuth2Session(client=client)
    token = oauth.fetch_token(token_url=token_url, auth=auth)
    print(token)

    # response = requests.get(secrets.REDIRECT_URI, params=params, auth=oauth)
    # print (response.status_code)

def get_kroger_code():
    krog_token_url = 'https://api.kroger.com/v1/connect/oauth2/token'
    krog_auth_url = 'https://api.kroger.com/v1/connect/oauth2/authorize'

    client_key = secrets.KROGER_CLIENT_ID
    client_secret = secrets.KROGER_CLIENT_SECRET
    redirect = secrets.REDIRECT_URI

    scopes = ['profile.compact', 'product.compact', 'cart.basic:write']
    oauth = OAuth2Session(client_id=client_key, redirect_uri=redirect, scope=scopes)
    authorization_url, state = oauth.authorization_url(krog_auth_url)
    webbrowser.open(authorization_url, new=2, autoraise=True)
    
    print()
    callback = input('Please paste the full callback URL from the browser: ')

    # callback_split = callback.split("=")

    # state_check = callback_split[2]
    # # if state == state_check:
    # #     pass
    # # else:
    # #     print("States are not equal... Terminate.")
    # #     sys.exit()

    # auth_long = callback_split[1].split("&state")
    # authorization_response = auth_long[0]

    token = oauth.fetch_token(krog_token_url, authorization_response=callback, client_secret=client_secret)
    # print(token)

    c = oauth.get('https://api.kroger.com/v1/cart/add')
    print(c)
    p = oauth.get('https://api.kroger.com/v1/products')
    print(p)

    
    
##########################
#########  MAIN ##########
##########################

if __name__ == "__main__":
    CACHE_DICT = load_cache()
    create_tables()

    # ##### Interactive #####
    flag = True # set flag'
    flag_a = True
    flag_c = False # set flag
    flag_d = False # set flag
    flag_e = False # set flag

    while flag == True:
        
        while flag_a == True: 
            print()
            recipe_query = input("Enter a recipe query (e.g. cake, pasta, burrito) or \"exit\": ").lower() 
            print()
            # force recipe_query to lower case
            
            if recipe_query == "exit":
                print()
                print("Goodbye!")
                sys.exit()
                
            else:
                # build recipe instances from recipe query
                recipe_dict = build_recipe_url_dict() 
                recipe_instances = []
                for recipe_url in recipe_dict[recipe_query]:
                    ins = get_recipe_instance(recipe_url)
                    recipe_instances.append(ins)

                print('-' * 40)
                print("List of", recipe_query.capitalize(), "recipes") # force all to capitalize for aesthetics 
                print('-' * 40)

                s = search_for_repeat()
                repeat_flag = False

                count = 1
                if len(recipe_instances) == 0:
                    print("No recipes related to query")
                    continue

                for recipe in recipe_instances[:20]: # only show 10 recipes
                    print("[" + str(count) + "] " + recipe.info())
                
                    for i in range(len(s)):
                        if recipe_query == str(s[i][0]):
                            repeat_flag = True

                    if repeat_flag == False:
                        # add recipe information to the database
                        rec_list = []
                        rec_list.append(recipe_query)
                        rec_list.append(str(recipe.name))
                        rec_list.append(str(recipe.rating))
                        rec_list.append(int(recipe.num_rating))
                        add_to_recipe_table(rec_list)

                        # add ingredients to the database
                        ingr_list = []
                        ingr_list.append(str(recipe.name))
                        ingr_list.append(str(recipe.ingredients))
                        ingr_list.append(int(recipe.servings))
                        ingr_list.append(str(recipe.nutrition))
                        add_to_ingredients_table(ingr_list)

                        rev_list = []
                        rev_list.append(str(recipe.name))
                        rev_list.append(str(recipe.review))
                        rev_list.append(int(recipe.num_review))
                        add_to_reviews_table(rev_list)

                    count += 1

                flag_a = False # input is valid
                flag_c = True # set flag
    
        # view the instructions or launch them in a web broswer
        # before or after ingredients?

        ############# INGREDIENTS #############
        while flag_c == True: 
            print()
            choice = input("Choose a recipe number for detailed ingredients or \"exit\" or \"back\": ")
            print()

            if choice.isnumeric() == False: 
                if choice == "exit":
                    print()
                    print("Goodbye!")
                    sys.exit()
                
                elif choice == "back":
                    flag_c = False # break out of the loop to go "back"
                    flag_a = True #do main first input again

                else:
                    print()
                    print("[Error] You must choose a number or \"exit\" or \"back\"")

            if choice.isnumeric() == True: 
                if int(choice) >= count:
                    print()
                    print("[Error] Choose a number within the list range")
                    #flag_c still True, loop around again for recipe number input

                else:
                    recipe_name = recipe_instances[:20][int(choice)-1]
                    ingr = recipe_name.ingredients
                    print('-' * 40)
                    print("Ingredients for", str(recipe_name.name)) # make sure this is the site that corresponds to the number 
                    print('-' * 40)
                    countv = 1
                    for i in ingr:
                        print("[" + str(countv) + "] " + str(i))
                        countv += 1
                    # flag_c2 = False
                    flag_c = False
                    flag_d = True # move on to cart part

        ############# CART #############
        while flag_d == True: 
            print()
            print("Would you like to add the recipe ingredients to a Kroger cart?")
            cart_choice = input("Enter \"yes,\" \"no,\" \"back,\" or \"exit\": ").lower()      
            print()

            if cart_choice == "exit":
                print()
                print("Goodbye!")
                sys.exit()
            
            elif cart_choice == "back": # should you go back to ingredients or ALL THE WAY BACK; back one at each level?
                flag_d = False # break out of the loop to go "back"
                flag_c = True
                break   

            elif cart_choice == "no": # to continue on 
                flag_d = False
                flag_e = True

            elif cart_choice != "exit" and cart_choice != "back" and cart_choice != "yes" and cart_choice != "no":
                print("[Error] You must choose \"yes,\" \"no,\" \"back,\" or \"exit\"")

            elif cart_choice == "yes":
                cart_list = []
                cart_list_owned = []
                for i in ingr:
                    cart_check = input("Do you have " + str(i) + "? (y/n): ").lower()
                    
                    if cart_check != "n" and cart_check != "y":
                        print("[Error] You must choose \"y\" or \"n\"")
                    
                    if cart_check == "y":
                        cart_list_owned.append(i)

                    if cart_check == "n":
                        cart_list.append(i)
                
                parsed_cart_list = ingredients_parsing([cart_list])
            
                ############# Kroger API #############
                print()
                print("You will have to log in to Kroger during authentication")
                print("Create a new Kroger account if you have security or access concerns")

                get_kroger_code()

        ############# PLOTS ############# 
        while flag_e == True: 
            print("Would you like to view recipe-related plots?")
            plot_choice = input("Enter \"yes,\" \"back,\" or \"exit\": ").lower()      
            print()

            if plot_choice == "exit":
                print()
                print("Goodbye!")
                sys.exit()

            elif plot_choice == "back":
                flag_e = False # break out of the loop to go "back"
                flag_d = True
                break  

            elif plot_choice != "exit" and plot_choice != "back" and plot_choice != "yes":
                print("[Error] You must choose \"yes,\" \"back,\" or \"exit\"")
            
            elif plot_choice == "yes":
                print("What kind of plot would you like to view?")
                print("[1] Nutrition Information (all recipes in query)")
                print("[2] Ratings vs. Reviews Numbers (all recipes in query)")
                print("[3] Allergen Information (all recipes in query)")
                print("[4] Common Words in Reviews (previously chosen recipe)")

                return_flag_2 = True
                while return_flag_2 == True:
                    print()
                    plot_num = input("Enter a plot number: ") 
                    if plot_num.isnumeric() == False: 
                        print()
                        print("Please enter a number")

                    elif plot_num.isnumeric() == True:
                        if int(plot_num) > 4:
                            print("[Error] Choose a number within the list range")
                        
                        elif int(plot_num) == 1:
                            plot_list_1 = []
                            recipe_name_list = []
                            for r in recipe_instances[:20]:
                                plot_list_1.append(str(r.nutrition))
                                recipe_name_list.append(str(r.name))

                            nutrition_plot(recipe_name_list, plot_list_1)
                            return_flag_2 = False

                        elif int(plot_num) == 2:
                            rating_list = []
                            review_list = []
                            recipe_name_list = []
                            for s in recipe_instances[:20]:
                                rating_list.append(s.num_rating)
                                review_list.append(s.num_review)
                                recipe_name_list.append(str(s.name))
                            
                            ratings_reviews_plot(recipe_name_list, rating_list, review_list)
                            return_flag_2 = False

                        elif int(plot_num) == 3:
                            plot_list_3 = []
                            recipe_names = []
                            for t in recipe_instances[:20]:
                                plot_list_3.append(t.ingredients)
                                recipe_names.append(str(t.name))
                            
                            cleaned_list = ingredients_parsing(plot_list_3) # feed output to allergen plot function
                            allergen_plot(recipe_names, cleaned_list)
                            return_flag_2 = False


                        elif int(plot_num) == 4:
                            plot_list_4 = []
                            plot_list_4.append(recipe_name.review) # top helpful review -- js was obscuring other reviews

                            review_plot(plot_list_4) # exclude first two because they're "highlighted" and might appear more than once
                            return_flag_2 = False