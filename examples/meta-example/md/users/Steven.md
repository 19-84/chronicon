[🏠 Home](../index.md) | [📋 Latest](../latest/index.md) | [🔥 Top](../top/replies/index.md) | [👥 Users](../users/index.md)

[Home](../index.md) » [Users](../users/index.md) » Steven

---

# Steven

> **Name:** Steven
> **Trust Level:** 2
> **Member Since:** 2015-04-10
> **Total Posts:** 15

---

## Recent Posts (15 of 15)

### [Air Theme](../t/air-theme/197703.md)
*Posted: 2024-04-01 16:51 | Post #511*

It may not be the cleanest way to do it, but add these lines in Desktop css
    
    
    .topic-list-data.num.views {
      display: unset;
    }
    td.topic-list-data.num.views {
      display: fle...

---

### [Air Theme](../t/air-theme/197703.md)
*Posted: 2024-03-05 13:24 | Post #496*

![](https://d3bpeqsaub0i6y.cloudfront.net/user_avatar/meta.discourse.org/gonerdot/48/366307_2.png) Gonerdot:

> There is some empty space at the top. Is there any way to remove it? I can’t find anythi...

---

### [Minima Theme](../t/minima-theme/108178.md)
*Posted: 2020-09-12 20:52 | Post #26*

Oh ok I understand better now

It comes from the header file : <https://github.com/discourse/minima/blob/master/desktop/header.html>

It rewrites the topic list template.

Original template : <https:/...

---

### [Minima Theme](../t/minima-theme/108178.md)
*Posted: 2020-09-12 19:08 | Post #24*

I believe this is the avatar on top of the topic title

[![image](https://d11a6trkgmumsb.cloudfront.net/optimized/3X/a/b/ab1dce04b8d04863fac29ec558b81d05a80a858c_2_690x173.png)](https://d11a6trkgmumsb...

---

### [Sam's Simple Theme](../t/sams-simple-theme/23552.md)
*Posted: 2020-04-15 13:35 | Post #320*

I edited my previous post, I got confused with all the different versions.

The code you added was for the newest version of Discourse. If I understand correctly, you need a to edit the header for a o...

---

### [Sam's Simple Theme](../t/sams-simple-theme/23552.md)
*Posted: 2020-04-15 10:49 | Post #318*

There already is a excerpt reference, so you might want to delete line 16 first
    
    
      {{raw "list/topic-excerpt" topic=model}}
    

Then, I would add this
    
    
      {{#if expandPinned...

---

### [Sam's Simple Theme](../t/sams-simple-theme/23552.md)
*Posted: 2020-04-15 00:24 | Post #316*

Yes the change in the avatar was in the version 2.5.0 beta 2.
  *[PR]: Pull Request

---

### [Sam's Simple Theme](../t/sams-simple-theme/23552.md)
*Posted: 2020-04-03 19:14 | Post #309*

It’s a little bug, it will be fixed soon.

If you want to fix it until then, you just need to edit the theme and in the Desktop > Header part, change the code with this

_((edited, upgrade the compone...

---

### [Graceful Theme](../t/graceful-theme/93040.md)
*Posted: 2020-03-23 12:10 | Post #74*

I’m not on my computer but I know there is some margin-left to correct with the class timeline-container
  *[PR]: Pull Request

---

### [Graceful Theme](../t/graceful-theme/93040.md)
*Posted: 2020-03-22 20:20 | Post #71*

topic-body has his own width setting.

Default:
    
    
    .topic-body {
        width: calc(690px + (11px * 2));
    }
    

Change only the 690px and keep the rest (it’s linked to the padding of ...

---

### [Sam's Simple Theme](../t/sams-simple-theme/23552.md)
*Posted: 2019-06-24 19:10 | Post #285*

You can edit the theme in the `Header` section

And replace it all with this:
    
    
    <script type='text/x-handlebars' data-template-name='list/topic-list-item.raw'>
    
    {{#if bulkSelectEna...

---

### [Sam's Simple Theme](../t/sams-simple-theme/23552.md)
*Posted: 2019-05-13 23:03 | Post #283*

I wanted to create a theme component who can work on a majority of themes, because I didn’t really know how to edit the topic-list-item.raw.hbs, I used your work as a base.

I used two parts of your t...

---

### [Sam's Simple Theme](../t/sams-simple-theme/23552.md)
*Posted: 2019-05-13 12:55 | Post #281*

Hello [@sam](/u/sam), is it ok if I use parts of your theme to do a theme component ?

I played with this this weekend and I think I can do a theme component for those interested
  *[PR]: Pull Request

---

### [Daemonite Material Theme](../t/daemonite-material-theme/64521.md)
*Posted: 2019-02-06 20:42 | Post #69*

I don’t use the theme, but my guess is:
    
    
    button.create .d-icon {
        color: #000;
    }
    

If it mess with other buttons, use this line instead
    
    
    #topic-footer-buttons ...

---

### [Daemonite Material Theme](../t/daemonite-material-theme/64521.md)
*Posted: 2019-02-05 22:51 | Post #66*

Use this in Common > CSS
    
    
    .d-header-icons .d-icon {
        color: #000;
    }
    
  *[PR]: Pull Request

---
