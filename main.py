from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv(override=True)

MOVIE_API_URL = "https://api.themoviedb.org/3/search/movie"
MOVIE_IMAGE_URL = "https://image.tmdb.org/t/p/w500"
MOVIE_DETAILS_URL = "https://api.themoviedb.org/3/movie/"

headers = {"Authorization": f"Bearer {os.getenv('MOVIE_API_ACCESS_TOKEN')}"}

app = Flask(__name__)
app.config["SECRET_KEY"] = "8BYkEfBA6O6donzWlSihBXox7C0sKR6b"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///movies.db"
Bootstrap5(app)


# CREATE DB
class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

db.init_app(app)


# CREATE TABLE
class Movie(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(String(255))
    rating: Mapped[float] = mapped_column(Float)
    ranking: Mapped[int] = mapped_column(Integer)
    review: Mapped[str] = mapped_column(String(255))
    img_url: Mapped[str] = mapped_column(String(255))


with app.app_context():
    db.create_all()

class RatingForm(FlaskForm):
    rating = StringField("Your rating out of 10 e.g. 7.5", validators=[DataRequired()])
    review = StringField("Your review", validators=[DataRequired()])
    submit = SubmitField("Submit")


@app.route("/")
def home():
    result = db.session.execute(db.select(Movie).order_by(Movie.rating.desc())).scalars()
    movie_list = result.all()

    for i, item in enumerate(movie_list):
        item.ranking = i+1
    
    db.session.commit()

    return render_template("index.html", all_movies=movie_list)


@app.route("/edit/<id>", methods=["GET", "POST"])
def edit(id):
    form = RatingForm()
    movie_to_update = db.get_or_404(Movie, id)
    if form.validate_on_submit():
        rating = form.rating.data
        review = form.review.data

        movie_to_update.rating = float(rating)
        movie_to_update.review = review

        db.session.commit()

        return redirect(url_for("home"))

    return render_template("edit.html", form=form, title=movie_to_update.title)


@app.route("/delete/<id>")
def delete(id):
    movie_to_delete = db.get_or_404(Movie, id)
    db.session.delete(movie_to_delete)
    db.session.commit()

    return redirect(url_for("home"))


class AddMovieForm(FlaskForm):
    movie_title = StringField("Movie Title", validators=[DataRequired()])
    add_movie = SubmitField("Add Movie")


@app.route("/add", methods=["GET", "POST"])
def add_movie():
    form = AddMovieForm()

    if form.validate_on_submit():

        searched_title = form.movie_title.data

        params = {"query": searched_title}

        movie_api_request = requests.get(
            url=MOVIE_API_URL, params=params, headers=headers
        )
        response = movie_api_request.json()["results"]
        movie_year_list = [
            {
                "id": movie.get("id"),
                "title": movie.get("original_title"),
                "release_date": movie.get("release_date"),
            }
            for movie in response
        ]

        return render_template("select.html", movie_list=movie_year_list)

    return render_template("add.html", form=form)


@app.route("/search/<id>")
def search_details(id):
    print(id)
    movie_details_request = requests.get(
        url=f"{MOVIE_DETAILS_URL}{int(id)}", headers=headers
    )
    response = movie_details_request.json()
    title = response.get("original_title")
    year = response.get("release_date").split("-")[0]
    desc = response.get("overview")
    image_url = MOVIE_IMAGE_URL + str(response.get("poster_path"))

    new_movie = Movie(
        title=title,
        year=year,
        description=desc,
        img_url=image_url,
        rating=0,
        ranking=0,
        review="n/a",
    )
    db.session.add(new_movie)
    db.session.commit()

    return redirect(url_for("edit", id=new_movie.id))


if __name__ == "__main__":
    app.run(debug=True)
