"""Demo seed data — lets the dashboard be demoed before the first live
YouTube ingestion run (or without an API key at all).

    python -m app.seed

Wipes all tracked data and inserts 12 realistic viral products with
multi-day metric histories, VADER-scored comment samples, transcripts,
and a plausible pipeline run log. The first real pipeline run simply
adds live videos alongside these; delete demo rows from the UI or
re-run this script any time.
"""

import asyncio
import math
import random
from datetime import timedelta

from sqlalchemy import delete

from .database import init_db, session_scope
from .models import (
    MetricsSnapshot,
    PipelineRun,
    QuotaUsage,
    SentimentAnalysis,
    TrackedKeyword,
    Transcript,
    Video,
)
from .services.sentiment import label_for, score_text
from .utils import quota_day_today, utcnow

random.seed(42)  # deterministic demo

GLOBAL_KEYWORDS = ["top trending products", "amazon finds", "tiktok made me buy it", "unboxing", "product review"]
CUSTOM_KEYWORDS = ["mini projector", "standing desk"]

# kw index: 0-4 globals, 5-6 customs
PRODUCTS = [
    {
        "id": "DEMO_000001", "kw": 2, "days": 5.6, "peak": 2_400_000, "like_pct": 5.8, "comment_pct": 0.42,
        "title": "This $24 Spray Mop Went VIRAL and I Finally Get Why (Repel-X Review)",
        "channel": "HomeHacks Daily", "duration": 624,
        "tags": ["spray mop", "cleaning hacks", "tiktok made me buy it", "amazon finds"],
        "midpoint": 0.55, "steep": 9,
        "pos": 81.0, "neg": 6.5, "neu": 12.5, "analyzed": 100,
        "comments": [
            ("Maria G.", "Bought this after seeing it everywhere and honestly it's the best cleaning purchase I've made all year. My floors have never looked better!", 2841),
            ("CleanFreakTL", "The microfiber pad picks up pet hair like magic. Obsessed.", 1203),
            ("Dave R.", "Okay the refillable bottle alone sold me. No more buckets. 10/10", 887),
            ("Jenna", "Mine arrived yesterday and the spray trigger already feels a little flimsy, hope it lasts", 432),
            ("Tidy w/ Tina", "I was skeptical because of the hype but it genuinely cuts my mopping time in half", 391),
            ("Mark Olsen", "It's fine. It's a mop. The internet needs to calm down lol", 240),
            ("Priya S.", "Third one of these viral cleaning gadgets I've bought and this is the only one that earned a spot in my closet", 198),
        ],
        "transcript": "Okay, I held out on this one for months. Every single cleaning account I follow has been pushing this Repel-X spray mop, and I finally caved so you don't have to. First impressions — it's light, the bottle clicks in like a Nerf cartridge, and the spray is a fine, even mist, not a puddle. I did my whole kitchen in about four minutes. The microfiber pad is washable, which means no refill subscription nonsense, and the pad actually grabs pet hair instead of pushing it around. Downsides? The trigger feels a bit plasticky and I'd baby it. But at twenty-four dollars, this beats my old bucket setup by a mile. Verdict: believe the hype on this one. Links below, and tell me what viral product I should test next.",
    },
    {
        "id": "DEMO_000002", "kw": 0, "days": 4.2, "peak": 1_850_000, "like_pct": 6.4, "comment_pct": 0.38,
        "title": "AuraGlow Sunset Lamp — The Most Aesthetic Gadget of the Year?",
        "channel": "GlowUp Reviews", "duration": 512,
        "tags": ["sunset lamp", "room decor", "aesthetic", "top trending products"],
        "midpoint": 0.45, "steep": 8,
        "pos": 76.4, "neg": 8.2, "neu": 15.4, "analyzed": 95,
        "comments": [
            ("ambercore", "my room literally looks like a pinterest board now. worth every penny", 3122),
            ("Liam K.", "Great for photos but the cord is comically short, mine barely reaches the outlet", 956),
            ("Sofia", "Bought two. No regrets. The golden hour setting is unreal for filming", 744),
            ("J. Patel", "It's pretty but it's also just... an orange light bulb? Mixed feelings", 502),
            ("photoby.nina", "As a portrait photographer this thing is secretly a $30 studio light. Shhh", 433),
            ("Tom", "Arrived broken the first time, replacement works great though. Seller was fast", 287),
        ],
        "transcript": "Sunset lamps took over everyone's feed about two years ago, and the AuraGlow is the latest version going viral — so is it actually different? Setup is literally plug and twist. The projection is sharper than my old one, with this deep amber gradient that makes any wall look like a movie scene. There are sixteen color modes now, but let's be honest, you'll use the classic sunset and never touch the rest. For creators, this is the cheat code: skin tones look incredible on camera. Two complaints — the cord is short, and the base is light enough that my cat relocated it twice. Still, for thirty bucks it transforms a room instantly. If you film content in your bedroom, this pays for itself in one video.",
    },
    {
        "id": "DEMO_000003", "kw": 1, "days": 6.1, "peak": 1_320_000, "like_pct": 4.9, "comment_pct": 0.51,
        "title": "I Tested the SnapChef Mini Chopper From My Amazon Finds List — WOW",
        "channel": "Kitchen Crusader", "duration": 738,
        "tags": ["kitchen gadgets", "amazon finds", "meal prep", "mini chopper"],
        "midpoint": 0.35, "steep": 7,
        "pos": 72.8, "neg": 9.1, "neu": 18.1, "analyzed": 100,
        "comments": [
            ("MealPrepMia", "Chopped a week of onions in 90 seconds and didn't cry once. Life changing", 1987),
            ("Carlos V.", "The blade is sharper than expected, be careful washing it! Learned the hard way", 1104),
            ("granny_approved", "I bought this for my arthritis and it has given me back my cooking. Thank you for reviewing it", 980),
            ("Ben", "It struggles a bit with carrots, you have to pre-cut them smaller", 511),
            ("Foodie Fran", "Garlic, herbs, nuts — does it all. The container is the perfect size for salsa too", 346),
            ("Kev", "decent but my food processor does the same thing? good for small kitchens i guess", 230),
        ],
        "transcript": "Today we're testing the SnapChef mini chopper, the one that keeps showing up on every Amazon finds list. Out of the box you get the chopper, two blade sets, and a storage lid for the bowl — that lid detail matters more than you think. I ran the gauntlet: onions, garlic, carrots, almonds, and a bunch of cilantro. Onions? Flawless, ninety seconds, zero tears. Garlic turned to perfect paste. Carrots were the only struggle — chunk them first or the motor labors. The pull-cord version needs no batteries, which is why I'd pick this over the electric ones for small kitchens. Cleanup is two parts, both dishwasher safe. For fifteen dollars this earns permanent counter space. That's a Kitchen Crusader seal of approval.",
    },
    {
        "id": "DEMO_000004", "kw": 2, "days": 3.4, "peak": 980_000, "like_pct": 7.1, "comment_pct": 0.33,
        "title": "Pillow Slides Are Back?? CloudNine Slides 30-Day Honest Test",
        "channel": "BuyOrBye", "duration": 595,
        "tags": ["pillow slides", "tiktok made me buy it", "comfy shoes"],
        "midpoint": 0.5, "steep": 10,
        "pos": 68.9, "neg": 13.6, "neu": 17.5, "analyzed": 90,
        "comments": [
            ("steph!", "Wore these every day for a month, my plantar fasciitis has never been happier", 1764),
            ("Jordan W.", "They squeak on tile floors and now my dog hates me", 1310),
            ("comfyqueen", "Sized up like the video said and they fit perfectly. So cloudlike", 689),
            ("Nick T.", "$12 well spent honestly. Shower shoes, house shoes, trash run shoes. Versatile king", 455),
            ("Ana", "Mine stretched out after two weeks of daily wear :( still comfy tho", 402),
            ("DrFeetPhD", "PSA: zero arch support, fine for lounging, do NOT run errands all day in these", 377),
        ],
        "transcript": "Pillow slides went mega viral in 2022, died, and now they're suddenly back on everyone's feed — so I wore the CloudNine slides every day for thirty days. Day one: yes, it genuinely feels like stepping on memory foam, that part is real. The thick EVA sole absorbs everything; standing in the kitchen for an hour, my feet weren't barking. Now the honest part. They run small — size up one. They squeak on hard floors. And after about two weeks the foam softens noticeably, so don't expect them to feel brand new forever. But at twelve dollars, the comfort-per-dollar ratio is absurd. Buy or bye? For house shoes, it's a confident buy. For anything involving actual walking outside — bye.",
    },
    {
        "id": "DEMO_000005", "kw": 4, "days": 5.0, "peak": 760_000, "like_pct": 5.2, "comment_pct": 0.47,
        "title": "HyperBrew Cold Espresso Maker Review: Coffee Shop Killer or Hype?",
        "channel": "The Review Lab", "duration": 812,
        "tags": ["espresso", "coffee gadgets", "product review", "cold brew"],
        "midpoint": 0.4, "steep": 7,
        "pos": 64.2, "neg": 15.3, "neu": 20.5, "analyzed": 100,
        "comments": [
            ("espresso_nerd", "The crema on a COLD extraction is genuinely impressive. Didn't think that was possible at this price", 1422),
            ("Hannah B.", "Saved me $6 a day. Paid for itself in three weeks. My wallet thanks you", 1015),
            ("CoffeeSnobAlert", "It's good but calling it 'espresso' is a stretch. It's strong coffee with foam", 873),
            ("Mike", "Cleaning all 5 parts every morning got old fast, just being honest", 644),
            ("latte.lyfe", "Works amazing with oat milk drinks!! The concentrate is so smooth", 391),
            ("R. Chen", "Mine leaked until I realized the seal was misaligned, check yours before returning it", 256),
        ],
        "transcript": "The HyperBrew claims to pull a cold espresso shot in under three minutes with no heat and no pressure machine — and that claim is mostly true. You load the basket with a fine grind, fill the chamber with room-temperature water, and pump. About forty pumps later you've got a concentrate with real crema. Blind-tasted against my actual espresso machine, the HyperBrew shot is smoother but flatter — less of that sharp espresso bite, which honestly suits iced lattes better. Where it loses points: five parts to clean every single use, and the pumping is a small arm workout. Where it wins: ninety dollars versus seven hundred, and it travels. If your coffee order is iced and milky, this thing will genuinely replace your café run.",
    },
    {
        "id": "DEMO_000006", "kw": 1, "days": 4.8, "peak": 540_000, "like_pct": 4.6, "comment_pct": 0.29,
        "title": "MagGrip 360 Car Mount — The Last Phone Mount You'll Ever Buy",
        "channel": "The Gear Guy", "duration": 451,
        "tags": ["car accessories", "phone mount", "amazon finds", "magsafe"],
        "midpoint": 0.3, "steep": 6,
        "pos": 74.5, "neg": 7.8, "neu": 17.7, "analyzed": 88,
        "comments": [
            ("RoadWarrior", "Survived a month of Boston potholes without budging. That's the only review that matters", 933),
            ("Tina M.", "The magnet is STRONG. Like, worry-about-your-credit-cards strong. Phone stays put", 705),
            ("Alex", "Doesn't work great with my thick otterbox case, had to use the metal ring insert", 489),
            ("DashCamDan", "Vent clip version blocks my AC less than expected. Solid build, all metal hinge", 314),
            ("Sam K.", "Bought one for each car and one for my wife. That's the endorsement", 268),
        ],
        "transcript": "Phone mounts are a graveyard of broken clips and sad suction cups, so when the MagGrip 360 started trending I had to torture test it. It's a metal ball joint with an absurdly strong magnet array — seventeen pounds of pull according to the box. I ran it on a dash mount and a vent clip for three weeks, including some genuinely terrible roads. The phone never moved. Not once. If you have MagSafe it just snaps on; older phones get a metal ring sticker, which works but is less elegant. One real caveat: thick rugged cases weaken the grip noticeably. The hinge stays tight, one-handed docking is effortless, and at twenty-two dollars it embarrasses mounts costing twice that. Gear Guy approved, full stop.",
    },
    {
        "id": "DEMO_000007", "kw": 3, "days": 6.8, "peak": 690_000, "like_pct": 3.1, "comment_pct": 0.58,
        "title": "Unboxing the PosturePal Pro — Does This Back Brace Actually Work?",
        "channel": "Honest Unbox", "duration": 689,
        "tags": ["posture corrector", "back brace", "unboxing", "health gadgets"],
        "midpoint": 0.25, "steep": 6,
        "pos": 41.3, "neg": 36.9, "neu": 21.8, "analyzed": 100,
        "comments": [
            ("PhysioPaul", "PT here: braces like this are a cue, not a cure. Wear it 30 min a day max and do the exercises", 2210),
            ("Derek", "Returned mine. Dug into my armpits within an hour and left marks", 1356),
            ("Lauren H.", "It reminds me to sit up which is honestly all I needed it to do", 820),
            ("skeptical_steve", "These things are the same $8 brace rebranded every year for $35. Look up the OEM listing", 791),
            ("Gina", "My shoulder pain got worse the week I used it daily. Be careful with sizing", 547),
            ("Marcus", "Works fine for desk sessions but you look like a tactical turtle wearing it", 412),
        ],
        "transcript": "The PosturePal Pro keeps appearing in everyone's ads with some bold claims, so let's unbox it and put a skeptical eye on this thing. In the box: the brace, an exercise pamphlet nobody will read, and a sizing chart that, spoiler, runs small. First wear — it does pull the shoulders back immediately, you feel taller. But within forty minutes, the straps press hard into the armpits, and that matches what physiotherapists keep saying: these are reminder devices, not fixes. The fabric quality is okay, stitching is reinforced where it counts. My verdict after a week: useful as a thirty-minute desk-posture alarm, useless and possibly counterproductive as an all-day crutch. At thirty-five dollars when near-identical braces sell for ten, the markup is the real story here.",
    },
    {
        "id": "DEMO_000008", "kw": 5, "days": 3.0, "peak": 1_150_000, "like_pct": 6.8, "comment_pct": 0.36,
        "title": "NebulaCast Mini Projector: $89 Home Cinema That Fits in Your Hand",
        "channel": "TechTomorrow", "duration": 904,
        "tags": ["mini projector", "home cinema", "tech review", "budget tech"],
        "midpoint": 0.6, "steep": 11,
        "pos": 78.6, "neg": 7.4, "neu": 14.0, "analyzed": 100,
        "comments": [
            ("MovieNightMomma", "Backyard movie nights are now a weekly thing in our house. Kids are obsessed", 2050),
            ("4KorNothing", "Set expectations: it's 1080p-ish in a dark room and that's exactly enough for $89", 1233),
            ("Trev", "The built in speaker is weak but it has bluetooth out so just pair a speaker. Solved", 860),
            ("Nina P.", "Auto keystone actually works! My ceiling movie setup took 2 minutes", 712),
            ("Raj", "Fan noise is audible in quiet scenes. Minor but worth knowing", 397),
            ("cinephile_carl", "Bought it expecting a toy, kept it as my travel projector. Pleasantly shocked", 305),
        ],
        "transcript": "Eighty-nine dollar projectors used to be e-waste with a lens, but the NebulaCast going viral right now is a different animal. It's palm-sized, runs Android TV natively, and auto-focuses with auto-keystone, which means you point it at literally any wall and it sorts itself out in seconds. Brightness is the honest conversation: in a dark room you get a gorgeous hundred-inch picture; with lights on, it washes out fast. The built-in speaker is laptop-tier, but Bluetooth out fixes that instantly. I measured the fan at a soft hum — noticeable in silent scenes, invisible in action movies. Netflix, YouTube, and Disney+ all run native. For dorm rooms, ceilings, and backyard movie nights, this is the easiest tech recommendation I've made all year.",
    },
    {
        "id": "DEMO_000009", "kw": 4, "days": 5.9, "peak": 430_000, "like_pct": 4.1, "comment_pct": 0.41,
        "title": "TurboVac Cordless Car Vacuum — Honest Review After 3 Weeks",
        "channel": "Viral Verdict", "duration": 568,
        "tags": ["car vacuum", "product review", "car detailing"],
        "midpoint": 0.3, "steep": 5,
        "pos": 58.7, "neg": 18.9, "neu": 22.4, "analyzed": 92,
        "comments": [
            ("DetailDevotee", "For crumbs and dust it's great. For sand after a beach trip, it taps out fast", 884),
            ("Kim", "The attachments hide inside the handle!! Why doesn't every vacuum do this", 672),
            ("Jay R.", "Battery died 12 minutes in on max mode. Fine for quick cleanups only", 545),
            ("CleanCarCrew", "Suction is better than my old corded one somehow. USB-C charging is so convenient", 433),
            ("Brittany", "Cute and works ok but the dust cup is tiny, emptied it 3x doing one car", 310),
        ],
        "transcript": "Car vacuums are where marketing goes to lie, so the TurboVac spent three weeks living in my trunk before this verdict. Build first: it's lighter than a water bottle, charges over USB-C, and the crevice tools store inside the handle, which is genuinely clever. Suction testing: cheerios, dust, and pet hair on fabric seats — handled, no drama. Beach sand ground into carpet — it struggled, and the tiny dust cup filled three times on one sedan. Battery reality check: about twenty-two minutes on standard, twelve on max. That's one thorough car, not two. So here's the verdict: as a keep-in-the-trunk crumb assassin for parents and commuters, easy recommend. As your only detailing tool, it's not trying to be that, and neither should you.",
    },
    {
        "id": "DEMO_000010", "kw": 0, "days": 2.4, "peak": 880_000, "like_pct": 6.1, "comment_pct": 0.31,
        "title": "GlowDrip LED Strip Pro: RGBIC Is the Upgrade Your Setup Needed",
        "channel": "Gadget Gal", "duration": 477,
        "tags": ["led lights", "gaming setup", "rgb", "top trending products"],
        "midpoint": 0.65, "steep": 12,
        "pos": 79.2, "neg": 6.1, "neu": 14.7, "analyzed": 85,
        "comments": [
            ("SetupSensei", "The rainbow wave effect without segments all being one color is why RGBIC wins. Looks pro", 1540),
            ("Mia", "Music sync mode at my house party was a certified hit. Guests kept asking about it", 977),
            ("budgetbuilds", "Adhesive is actually 3M this time, not the fake stuff that falls at 2am", 651),
            ("Chris L.", "App is a little cluttered but the presets are solid. Warm white mode for movie nights = chef kiss", 488),
            ("Tay", "30 feet for $25?? my whole ceiling perimeter is done and glowing", 360),
        ],
        "transcript": "LED strips are everywhere, but the GlowDrip Pro going viral this week earns the hype on one feature: RGBIC. Translation — instead of the whole strip being one color, segments animate independently, so you get flowing rainbow and meteor effects that look straight out of a pro streaming setup. Installation took me eleven minutes around a ceiling perimeter, and the adhesive is real 3M tape, which veterans of the great 2-AM-strip-collapse will appreciate. The app does scenes, schedules, and music sync that actually stays on beat. Color accuracy is vivid; the warm white is genuinely usable as ambient lighting, not that weird blue-white cheap strips do. Thirty feet, twenty-five dollars, controller included. For gamers, streamers, and dorm decorators, this is the easiest glow-up per dollar on the market.",
    },
    {
        "id": "DEMO_000011", "kw": 2, "days": 4.5, "peak": 510_000, "like_pct": 5.5, "comment_pct": 0.35,
        "title": "AquaPulse Water Flosser: My Dentist Asked What Changed",
        "channel": "TrendTested", "duration": 542,
        "tags": ["water flosser", "oral care", "tiktok made me buy it", "self care"],
        "midpoint": 0.35, "steep": 6,
        "pos": 75.8, "neg": 8.9, "neu": 15.3, "analyzed": 90,
        "comments": [
            ("FlossBoss", "Two months in and my gums stopped bleeding completely. Should've bought one years ago", 1105),
            ("Em", "Warning: aim it BEFORE turning it on. My bathroom mirror learned this lesson", 998),
            ("Dr. Sandra (real dentist)", "These are a great adjunct to string floss, not a replacement. But patients actually USE them, which matters more", 943),
            ("Greg", "Battery lasted 3 weeks per charge for me. Travel case is sturdy too", 380),
            ("mouthcarestan", "The cordless tank is small, you'll refill once mid-session. Minor annoyance", 295),
        ],
        "transcript": "I'm someone who lied to my dentist about flossing for a decade, so when the AquaPulse went viral I was the perfect test subject. It's a cordless water flosser with three pressure modes and a tank that lasts about forty-five seconds of continuous blasting. First use is a learning curve — aim first, then power, unless you want to repaint your mirror. But the results crept up on me: by week three, zero bleeding, and my hygienist asked what changed at my checkup. That sentence alone sells the thing. Real talk: the tank needs one mid-session refill, and dentists will remind you it complements rather than replaces string floss. But a tool you actually use daily beats a perfect one you avoid. Forty dollars for a better checkup? Done.",
    },
    {
        "id": "DEMO_000012", "kw": 6, "days": 6.5, "peak": 350_000, "like_pct": 2.4, "comment_pct": 0.62,
        "title": "FlexiDesk Riser: The Viral Standing Desk Converter That Let Me Down",
        "channel": "DeskSetup Dan", "duration": 655,
        "tags": ["standing desk", "desk setup", "wfh", "ergonomics"],
        "midpoint": 0.2, "steep": 5,
        "pos": 22.6, "neg": 55.8, "neu": 21.6, "analyzed": 98,
        "comments": [
            ("WFHWarrior", "Mine started wobbling at full height within a week. A monitor should not sway while I type", 1820),
            ("Dan is right", "Returned it after the gas spring started sinking under a single monitor. Quality control is a lottery", 1244),
            ("ErgoElla", "The keyboard tray flexes when you type hard. That's a dealbreaker for the main use case??", 902),
            ("Pete", "Mine has been fine for a month? Sounds like a QC lottery honestly", 677),
            ("Standing Sam", "Thank you for being honest while every other creator shills this thing", 590),
            ("cubicle_carl", "The viral clips conveniently never show anyone actually typing on it at full height lol", 415),
        ],
        "transcript": "This one hurts, because I wanted to love the FlexiDesk riser — the clips of it gliding up with one hand are everywhere and the price undercuts every competitor by half. Here's what three weeks of daily use revealed. The gas spring lift is smooth, that part's real. But at full standing height, the whole platform wobbles when you type — we measured over an inch of monitor sway. Worse, my unit's spring began sinking under a thirteen-pound monitor, which is... a monitor. The keyboard tray flexes audibly. Comments are full of identical stories, alongside lucky owners whose units are fine, which screams quality control lottery. At sixty dollars the temptation is real, but a standing desk you can't type on isn't a desk. Save up for the proven brands; skip this one.",
    },
]


def logistic_curve(n_points: int, peak: int, steep: float, midpoint: float) -> list[int]:
    """Monotonic S-curve with mild noise — looks like a real viral spike."""
    base = peak * 0.012
    series: list[int] = []
    for i in range(n_points):
        x = i / max(1, n_points - 1)
        v = base + (peak - base) / (1 + math.exp(-steep * (x - midpoint)))
        v *= 1 + random.uniform(-0.012, 0.012)
        series.append(int(max(0, v)))
    for i in range(1, n_points):
        series[i] = max(series[i], series[i - 1])
    return series


async def seed() -> None:
    await init_db()
    now = utcnow()

    async with session_scope() as db:
        # Wipe in FK-safe order, then rebuild a deterministic demo state.
        for table in (SentimentAnalysis, Transcript, MetricsSnapshot, Video, PipelineRun, QuotaUsage, TrackedKeyword):
            await db.execute(delete(table))
        await db.commit()

        keywords: list[TrackedKeyword] = []
        for kw in GLOBAL_KEYWORDS:
            keywords.append(TrackedKeyword(keyword=kw, kind="global", is_active=True))
        for kw in CUSTOM_KEYWORDS:
            keywords.append(TrackedKeyword(keyword=kw, kind="custom", is_active=True))
        for i, kw in enumerate(keywords):
            kw.last_searched_at = now - timedelta(hours=2 * (i % 4), minutes=random.randint(0, 50))
            kw.search_count = random.randint(18, 60)
            db.add(kw)
        await db.commit()
        for kw in keywords:
            await db.refresh(kw)

        # The two freshest uploads were only just picked up by discovery, so
        # they count as "new in last 24h" and show a sharp, recent spike.
        freshly_discovered = {"DEMO_000010", "DEMO_000008"}

        total_new = 0
        for p in PRODUCTS:
            published = now - timedelta(days=p["days"], hours=random.uniform(0, 5))
            if p["id"] in freshly_discovered:
                first_seen = now - timedelta(hours=random.uniform(3, 20))
            else:
                first_seen = published + timedelta(hours=random.uniform(6, 16))
            captures: list = []
            t = first_seen
            while t < now - timedelta(minutes=20):
                captures.append(t)
                t += timedelta(hours=2)
            captures.append(now - timedelta(minutes=random.randint(4, 18)))
            n = len(captures)

            views = logistic_curve(n, p["peak"], p["steep"], p["midpoint"])
            like_ratio = p["like_pct"] / 100
            comment_ratio = p["comment_pct"] / 100
            likes = [int(v * like_ratio * (1 + random.uniform(-0.03, 0.03))) for v in views]
            comments = [int(v * comment_ratio * (1 + random.uniform(-0.04, 0.04))) for v in views]
            for i in range(1, n):
                likes[i] = max(likes[i], likes[i - 1])
                comments[i] = max(comments[i], comments[i - 1])

            hours_gap = (captures[-1] - captures[-2]).total_seconds() / 3600
            view_velocity = round((views[-1] - views[-2]) / hours_gap, 2)
            like_velocity = round((likes[-1] - likes[-2]) / hours_gap, 2)

            kw = keywords[p["kw"]]
            video = Video(
                video_id=p["id"],
                title=p["title"],
                description=f"{p['title']} — full hands-on review. Timestamps and links in the description. "
                            "Subscribe for weekly viral product testing.",
                channel_id=f"UCdemo{p['id'][-4:]}",
                channel_title=p["channel"],
                published_at=published,
                thumbnail_url=f"https://picsum.photos/seed/{p['id']}/640/360",
                duration_seconds=p["duration"],
                tags=p["tags"],
                discovered_keyword_id=kw.id,
                first_seen_at=first_seen,
                last_refreshed_at=captures[-1],
                latest_view_count=views[-1],
                latest_like_count=likes[-1],
                latest_comment_count=comments[-1],
                view_velocity=view_velocity,
                like_velocity=like_velocity,
                like_ratio=round(likes[-1] / views[-1] * 100, 3),
                sentiment_positive_pct=p["pos"],
                sentiment_negative_pct=p["neg"],
                sentiment_neutral_pct=p["neu"],
                transcript_status="ok",
            )
            db.add(video)
            total_new += 1

            for i in range(n):
                db.add(
                    MetricsSnapshot(
                        video_id=p["id"], captured_at=captures[i],
                        view_count=views[i], like_count=likes[i], comment_count=comments[i],
                    )
                )

            # Score the authored comments with the real VADER engine so labels,
            # compounds, and the aggregate row are internally consistent.
            samples = []
            compound_sum = 0.0
            for j, (author, text, likes_n) in enumerate(p["comments"]):
                compound = round(score_text(text), 4)
                compound_sum += compound
                samples.append(
                    {
                        "author": author, "text": text, "like_count": likes_n,
                        "published_at": (published + timedelta(hours=8 + j * 9)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "reply_count": random.randint(0, 40),
                        "compound": compound, "label": label_for(compound),
                    }
                )
            avg_compound = round(compound_sum / len(samples), 4)
            video.sentiment_compound = avg_compound
            db.add(
                SentimentAnalysis(
                    video_id=p["id"], computed_at=captures[-1], comments_analyzed=p["analyzed"],
                    positive_pct=p["pos"], negative_pct=p["neg"], neutral_pct=p["neu"],
                    avg_compound=avg_compound, sample_comments=samples,
                )
            )

            text = p["transcript"]
            db.add(
                Transcript(
                    video_id=p["id"], status="ok", language="en", source="youtube-transcript-api",
                    content=text, word_count=len(text.split()), fetched_at=first_seen + timedelta(hours=2),
                )
            )

        # A plausible run log: 9 completed cycles every ~2h + today's quota ledger.
        units_today = 0
        for i in range(9, 0, -1):
            started = now - timedelta(hours=2 * i, minutes=random.randint(0, 18))
            duration = timedelta(seconds=random.randint(35, 160))
            units = random.choice([302, 303, 305, 308, 311])
            run = PipelineRun(
                started_at=started, finished_at=started + duration,
                status="success" if i != 4 else "partial",
                trigger="scheduled" if i != 1 else "manual",
                keywords_searched=random.sample([k.keyword for k in keywords], 3),
                videos_discovered=random.randint(0, 4), videos_refreshed=random.randint(28, 64),
                comments_fetched=random.randint(300, 900), transcripts_fetched=random.randint(0, 3),
                sentiment_computed=random.randint(3, 11), quota_units_used=units,
                error="sentiment DEMO_000009: transient HTTP 503 from commentThreads.list (retried next cycle)"
                if i == 4 else None,
            )
            db.add(run)
            if started.strftime("%Y-%m-%d") == quota_day_today():
                units_today += units
        db.add(QuotaUsage(quota_date=quota_day_today(), units=units_today or 612))
        await db.commit()

    print(f"Seeded {total_new} demo videos with full history, sentiment, and transcripts.")
    print("The first live pipeline run will add real YouTube data alongside these.")


if __name__ == "__main__":
    asyncio.run(seed())
