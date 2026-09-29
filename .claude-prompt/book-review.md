# Admin view

I would like there to be an admin view I can log into to do some content management. To start, we'll make a page with a form to generate book reviews.

The admin view of the website should not have a button to get there from the homepage - I will go directly to the URL. If not yet logged in, it should take me to a login page. It should perform auth with a username and password. Determine how best to architect the storage and I will implement what is needed in Amazon.

When I login to the admin view, the "homepage" should basically be a list of buttons for actions I can perform. So to start it will just have one button to upload a book review.

The book review page will have the following components

* Text fields for Title and Author
* When I write my reviews, I name what facets go into the review, weight how important each one is to the work, and then score the book on each facet.
    * There should be some UI where I can add/remove facets and adjust their weights.
    * Following that, a place to rate each facet
    * The default facets should be: Characters, Atmosphere, Writing, Plot, Intrigue, Logic, and Enjoyment. The default weights should be equal.
* My reviews optionally include a timeline with a freetext fields for thoughts I had at that point in the book (stored as a percentage through the book). There should be a UI element to add/remove those.
    * Skip this by default
* My reviews optionally include a freetext review of the book as a whole. Include a UI element to allow input of this.