[🏠 Home](../index.md) | [📋 Latest](../latest/index.md) | [🔥 Top](../top/replies/index.md) | [👥 Users](../users/index.md)

[Home](../index.md) » [Users](../users/index.md) » Arkshine

---

# Arkshine

> **Name:** Arkshine
> **Trust Level:** 3
> **Member Since:** 2018-01-15
> **Total Posts:** 31

---

## Recent Posts (31 of 31)

### [Material Design Theme](../t/material-design-theme/47142.md)
*Posted: 2025-04-01 19:22 | Post #417*

[@Stephane_Roy](/u/stephane_roy)

You’re right. I tested on a _production_ server, and the error is still showing.  
I would wait for the team to take a look. I’m not sure how to fix it at the moment....

---

### [Material Design Theme](../t/material-design-theme/47142.md)
*Posted: 2025-04-01 14:22 | Post #415*

If you rebuild Discourse, that should fix the issue.

A fix was merged recently about it: [DEV: Allow stylesheet entrypoints to use `@use` (#31905) · discourse/discourse@b1924c3 · GitHub](https://gith...

---

### [Heroes - Fantasy Theme](../t/heroes-fantasy-theme/354452.md)
*Posted: 2025-02-25 17:36 | Post #3*

[![A beautifully illustrated scroll stating "Beautiful" in elegant, decorative lettering lies on a wooden surface, evoking a vintage or timeless feel. \(Captioned by AI\)](https://d11a6trkgmumsb.cloud...

---

### [A reddit-ish theme for Discourse](../t/a-reddit-ish-theme-for-discourse/269466.md)
*Posted: 2025-02-25 15:13 | Post #110*

Odd, it works for me:

[![image](https://d11a6trkgmumsb.cloudfront.net/original/4X/3/7/e/37eed9f627a132b7ca802736306390538b67421b.png)](https://d11a6trkgmumsb.cloudfront.net/original/4X/3/7/e/37eed9f6...

---

### [A reddit-ish theme for Discourse](../t/a-reddit-ish-theme-for-discourse/269466.md)
*Posted: 2025-02-25 14:59 | Post #108*

[@Damian_Boon](/u/damian_boon) Go to the theme settings; you will see the translations below.

![image](https://d11a6trkgmumsb.cloudfront.net/original/4X/7/8/4/7841dbd913d66ba7ba48409faa630dd9a46d5f7b...

---

### [A reddit-ish theme for Discourse](../t/a-reddit-ish-theme-for-discourse/269466.md)
*Posted: 2025-02-23 18:03 | Post #104*

I’ve installed it on Theme Creator; you can give it a try: [Theme Creator](https://discourse.theme-creator.io/theme/Arkshine/redditish)
  *[PR]: Pull Request

---

### [Air Theme](../t/air-theme/197703.md)
*Posted: 2025-02-21 00:47 | Post #561*

Interesting. I have no idea at the moment. I can’t reproduce it on the latest or even your version.

For reference, you’re using Discourse 3.3.3.

By the way, is there a specific reason? The latest “[...

---

### [Air Theme](../t/air-theme/197703.md)
*Posted: 2025-02-20 22:25 | Post #559*

Do you see any error in the browser’s console and also in _yoursite_ /logs ?
  *[PR]: Pull Request

---

### [Air Theme](../t/air-theme/197703.md)
*Posted: 2025-02-20 22:23 | Post #557*

Do you get the same error every time you try to install this theme?
  *[PR]: Pull Request

---

### [FKB Pro - Social theme](../t/fkb-pro-social-theme/234323.md)
*Posted: 2025-02-18 20:03 | Post #413*

The SCSS mixin `sticky` has been removed from core recently ([DEV: Remove unnecessary scss mixins (#31355) · discourse/discourse@46c568a · GitHub](https://github.com/discourse/discourse/commit/46c568a...

---

### [FKB Pro - Social theme](../t/fkb-pro-social-theme/234323.md)
*Posted: 2025-02-17 14:50 | Post #411*

[@Jun](/u/jun) You can achieve that with the TC settings.

Here is what you can do.  
First, define the global style: width, style and radius:  


[![The image shows various control elements for custo...

---

### [FKB Pro - Social theme](../t/fkb-pro-social-theme/234323.md)
*Posted: 2025-02-17 03:36 | Post #408*

Do you mean you want the callouts style the same as the quote?  
For example,  


[![Screenshot 2024-05-23 at 22.05.18.jpeg 2](https://d11a6trkgmumsb.cloudfront.net/optimized/4X/8/7/2/8724d30ffc5d9727...

---

### [Graceful Theme](../t/graceful-theme/93040.md)
*Posted: 2025-02-16 17:20 | Post #148*

The Canapin’s TC works for me on this theme.  
This TC sets `--d-max-width` and `--topic-body-width` CSS variables.  
You might have another TC or customizations that overwrites these values.

You can...

---

### [Mint Theme](../t/mint-theme/202822.md)
*Posted: 2024-07-18 15:25 | Post #52*

Sure,

You can create a new theme component, attach it to your theme, and add the following CSS:
    
    
    .custom-search-banner-wrap {
        h1 {
            color: blue; /* headline*/
        ...

---

### [Mint Theme](../t/mint-theme/202822.md)
*Posted: 2024-06-14 14:48 | Post #48*

This is the related CSS:

[github.com/discourse/discourse-mint-theme](https://github.com/discourse/discourse-mint-theme/blob/main/desktop/desktop.scss#L19-L46)

#### [desktop/desktop.scss](https://git...

---

### [Mint Theme](../t/mint-theme/202822.md)
*Posted: 2024-06-14 12:49 | Post #44*

It does work on my side. Maybe it misses a `height: auto`, though.

Here is what I did. I created a theme component attached to the theme.

[![image](https://d11a6trkgmumsb.cloudfront.net/optimized/4X...

---

### [Mint Theme](../t/mint-theme/202822.md)
*Posted: 2024-06-14 00:32 | Post #42*

![](https://avatars.discourse-cdn.com/v4/letter/g/6de8d8/48.png) Gabriel Vianna:

> Is it possible to change this green theme?

In the theme settings, you can edit the color palette:

[![image](https:...

---

### [Isabelle, an Animal Crossing inspired theme](../t/isabelle-an-animal-crossing-inspired-theme/145005.md)
*Posted: 2024-03-23 04:41 | Post #45*

Hi! Discourse includes, by default, the chat and should appear in all themes as long it’s enabled!
  *[PR]: Pull Request

---

### [Sam's Simple Theme](../t/sams-simple-theme/23552.md)
*Posted: 2024-03-20 21:26 | Post #369*

You can add the following CSS in a new theme component:
    
    
    img.avatar {
      border-radius: 3px;
    }
    

![image](/secure-uploads/original/4X/b/3/d/b3d2cf756e4a72c6ee7ed8032674ea964926...

---

### [Air Theme](../t/air-theme/197703.md)
*Posted: 2024-03-15 19:56 | Post #506*

I see the same issue with the default Color Scheme (I did not switch the scheme before).

Oddly, the background and the icon use the same `--primary-low-mid` color, and I can’t see any recent changes ...

---

### [Air Theme](../t/air-theme/197703.md)
*Posted: 2024-03-04 17:07 | Post #493*

I tested my CSS, and it works for me. Did you test it?

![](https://d3bpeqsaub0i6y.cloudfront.net/user_avatar/meta.discourse.org/gonerdot/48/366307_2.png) Gonerdot:

> I tried to hide them this way

I...

---

### [Air Theme](../t/air-theme/197703.md)
*Posted: 2024-03-04 16:58 | Post #491*

You can try this CSS:
    
    
    .topic-list {
        .topic-list-header .posts,
        .topic-list-body .posts {
            display: none !important;   
        }
    }
    
    
  *[PR]: Pull ...

---

### [Air Theme](../t/air-theme/197703.md)
*Posted: 2024-02-15 23:25 | Post #484*

No need to apologize. It may not be commonly known that you can do that! 😄

Here’s a guide if you want to explore the theme/components:

![](https://d3bpeqsaub0i6y.cloudfront.net/user_avatar/meta.disc...

---

### [FKB Pro - Social theme](../t/fkb-pro-social-theme/234323.md)
*Posted: 2024-01-30 18:26 | Post #273*

Can you try this CSS?

I’m not sure if showing the parent category color looks good here. ![:thinking:](https://emoji.discourse-cdn.com/twitter/thinking.png?v=12)
    
    
    .badge-category__wrappe...

---

### [Mint Theme](../t/mint-theme/202822.md)
*Posted: 2024-01-24 14:40 | Post #38*

Welcome! 👋

There is a theme component installed automatically with this theme.

It’s called [Search Banner](https://meta.discourse.org/t/search-banner/122939).

Usually theme components has settings ...

---

### [Transit - A Public Tranportation theme](../t/transit-a-public-tranportation-theme/292129.md)
*Posted: 2024-01-18 22:45 | Post #3*

Looks super clean! Good job!
  *[PR]: Pull Request

---

### [FKB Pro - Social theme](../t/fkb-pro-social-theme/234323.md)
*Posted: 2023-12-30 18:44 | Post #252*

To complete Ondrej’s answer, you can create a new theme component, attach it to your theme, and apply all your customizations here. 👍

![image](/secure-uploads/original/4X/b/d/9/bd94e86d3aca63fd10df5e...

---

### [Sam's Simple Theme](../t/sams-simple-theme/23552.md)
*Posted: 2023-11-20 05:16 | Post #366*

Hm, I’m unable to reproduce ![:thinking:](https://emoji.discourse-cdn.com/twitter/thinking.png?v=12)

As a side note, this user card modal is from this theme component: [Usercard Redesign Experiment](...

---

### [Fully Theme](../t/fully-theme/262833.md)
*Posted: 2023-11-15 12:42 | Post #82*

Try this CSS.

![image](/secure-uploads/original/4X/b/b/6/bb6cfbb7c6de23be35411e72da9d20ca87ad94c3.png)
    
    
    .d-header {
        height: auto;
        padding-bottom: 0.5em;
    }
    
    .d...

---

### [Fully Theme](../t/fully-theme/262833.md)
*Posted: 2023-11-14 23:04 | Post #80*

For any themes (or components) installed from a URL, you will not see a button to edit HTML/CSS. It’s because, on update, it will overwrite your changes.

You can either propose your changes to the th...

---

### [Air Theme](../t/air-theme/197703.md)
*Posted: 2023-04-02 23:16 | Post #372*

Hi, welcome back 👋

You don’t need to modify your theme. Unless I misunderstand, you can set up Google Analytics in the admin settings (`Basic Setup` or type `ga` in the search bar)

[![image](https:/...

---
