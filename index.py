import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

data = pd.read_csv('data.csv')
# Fix future warning
data['BMI_Range'] = data['BMI_Range'].replace(
    {'Unknown': np.NAN}).astype('category')
# Use -1 as a specific value for missing data
data['Veg/NonVeg'] = data['Veg/NonVeg'].fillna(-1).astype(int)
data['Sugars'].fillna(data['Sugars'].mean(), inplace=True)
# Use mode for categorical data
data['BMI_Range'].fillna(data['BMI_Range'].mode()[0], inplace=True)


def calculate_bmr(weight, height, age, gender):
    return 10 * weight + 6.25 * height - 5 * age + (-161 if gender == 'F' else 5)
x

def extract_params(param_str):
    params = {}
    params["Gender"] = param_str[0]
    params["Height"] = int(param_str[1:4])
    params["Age"] = int(param_str[4:6])
    params["Diet"] = int(param_str[6])
    params["Activity"] = int(param_str[7])
    params["Goal"] = int(param_str[8])
    weight_slice = -2 if len(param_str) == 11 else -3
    params["Weight"] = int(param_str[weight_slice:])
    return params


def calculate_calorie_requirement(bmr, activity_level):
    activity_factors = {'sedentary': 1.2, 'lightly_active': 1.375,
                        'moderately_active': 1.55, 'very_active': 1.725, 'extra_active': 1.9}
    activity_factor = activity_factors.get(activity_level, 1.2)
    return bmr * activity_factor


def recommend_all_foods_and_goal(data, veg_nonveg, goal):
    if veg_nonveg not in [1, 0] or goal not in [1, 2, 0]:
        raise ValueError(
            "Invalid input for vegetarian/non-vegetarian or goal.")

    foods_df = data[data['Veg/NonVeg'] == veg_nonveg]
    recommended_meals = {}

    for index, row in foods_df.iterrows():
        meal = 'Breakfast' if row['Breakfast'] == 1 else (
            'Lunch' if row['Lunch'] == 1 else 'Dinner')
        food_item = {
            'Meal': meal,
            'Veg/NonVeg': veg_nonveg,
            **{col: row[col] for col in foods_df.columns if col not in ['Breakfast', 'Lunch', 'Dinner', 'Food_items']},
            'BMI_Range': {3: 'Healthy', 4: 'Overweight', 1: 'Underweight', 2: 'Normal'}.get(row['BMI_Range'], 'Unknown')
        }

        if goal == 1 and any(food_item[nutrient] > threshold for nutrient, threshold in zip(['Calories', 'Proteins', 'Fats', 'Carbohydrates'], [300, 25, 20, 50])):
            recommended_meals[row['Food_items']] = food_item
        elif goal == 2 and any(food_item[nutrient] < threshold for nutrient, threshold in zip(['Calories', 'Proteins', 'Fats', 'Carbohydrates'], [300, 20, 10, 50])):
            recommended_meals[row['Food_items']] = food_item
        elif goal == 0 and all(lower <= food_item[nutrient] <= upper for nutrient, lower, upper in zip(['Calories', 'Proteins', 'Fats', 'Carbohydrates'], [300, 15, 10, 40], [400, 25, 20, 60])):
            recommended_meals[row['Food_items']] = food_item

    return {"count": len(recommended_meals), "meals": recommended_meals}


def process_params(param_str):
    params = extract_params(param_str)
    weight = params["Weight"]
    height = params["Height"]
    age = params["Age"]
    gender = params["Gender"]
    bmr = calculate_bmr(weight, height, age, gender)

    activity_level_mapping = {'sedentary': 1, 'lightly_active': 2,
                              'moderately_active': 3, 'very_active': 4, 'extra_active': 5}
    activity_level = list(activity_level_mapping.keys())[
        params["Activity"] - 1]

    calorie_requirement = calculate_calorie_requirement(bmr, activity_level)

    veg_nonveg = params["Diet"]
    goal = params["Goal"]
    recommended_meals_dict = recommend_all_foods_and_goal(
        data.copy(), veg_nonveg, goal)

    return recommended_meals_dict


@app.get("/")
async def root():
    return {'message': 'Welcome to the Meal Recommendation API'}


@app.get("/meal/{param}")
async def get_meals(param: str):
    try:
        recommended_meals = process_params(param)
        return recommended_meals
    except ValueError as e:
        return {'error': str(e)}
