"""
Batch adds Workday companies from the user's list.
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "us_ats_jobs")))

import db.database as database

# Parsed from user text
WORKDAY_URLS = [
    "acxiomllc.wd5.myworkdayjobs.com", "agilent.wd5.myworkdayjobs.com", "alcon.wd5.myworkdayjobs.com",
    "ankura.wd5.myworkdayjobs.com", "broadridge.wd5.myworkdayjobs.com", "campaignmonitor.wd5.myworkdayjobs.com",
    "cefcu.wd5.myworkdayjobs.com", "comcast.wd5.myworkdayjobs.com", "corelogic.wd5.myworkdayjobs.com",
    "crowdstrike.wd5.myworkdayjobs.com", "discover.wd5.myworkdayjobs.com", "disney.wd5.myworkdayjobs.com",
    "earlywarning.wd5.myworkdayjobs.com", "empower.wd5.myworkdayjobs.com", "fiserv.wd5.myworkdayjobs.com",
    "flagstar.wd5.myworkdayjobs.com", "gsk.wd5.myworkdayjobs.com", "harbourvest.wd5.myworkdayjobs.com",
    "hcmportal.wd5.myworkdayjobs.com", "hq.wd5.myworkdayjobs.com", "kyriba.wd5.myworkdayjobs.com",
    "liveramp.wd5.myworkdayjobs.com", "mii.wd5.myworkdayjobs.com", "nationalindemnity.wd5.myworkdayjobs.com",
    "navexglobal.wd5.myworkdayjobs.com", "nrel.wd5.myworkdayjobs.com", "nvidia.wd5.myworkdayjobs.com",
    "ouryahoo.wd5.myworkdayjobs.com", "portlandgeneral.wd5.myworkdayjobs.com", "powerdesigninc.wd5.myworkdayjobs.com",
    "q2ebanking.wd5.myworkdayjobs.com", "redriver.wd5.myworkdayjobs.com", "scj.wd5.myworkdayjobs.com",
    "thehartford.wd5.myworkdayjobs.com", "toppanmerrill.wd5.myworkdayjobs.com", "travelers.wd5.myworkdayjobs.com",
    "troweprice.wd5.myworkdayjobs.com", "unisys.wd5.myworkdayjobs.com", "vanguard.wd5.myworkdayjobs.com",
    "verizon.wd5.myworkdayjobs.com", "vhr-pbs.wd5.myworkdayjobs.com", "walmart.wd5.myworkdayjobs.com",
    "westernunion.wd5.myworkdayjobs.com", "workday.wd5.myworkdayjobs.com", "zoom.wd5.myworkdayjobs.com",
    "accenture.wd3.myworkdayjobs.com", "amadeus.wd3.myworkdayjobs.com", "asml.wd3.myworkdayjobs.com",
    "aveva.wd3.myworkdayjobs.com", "baicommunications.wd3.myworkdayjobs.com", "belron.wd3.myworkdayjobs.com",
    "ci.wd3.myworkdayjobs.com", "covestro.wd3.myworkdayjobs.com", "db.wd3.myworkdayjobs.com",
    "elekta.wd3.myworkdayjobs.com", "gresearch.wd3.myworkdayjobs.com", "mckesson.wd3.myworkdayjobs.com",
    "mufgub.wd3.myworkdayjobs.com", "philips.wd3.myworkdayjobs.com", "refinitiv.wd3.myworkdayjobs.com",
    "swift.wd3.myworkdayjobs.com", "talentmanagementsolution.wd3.myworkdayjobs.com", "volarisgroup.wd3.myworkdayjobs.com",
    "salesforce.wd12.myworkdayjobs.com", "americanredcross.wd1.myworkdayjobs.com", "amgen.wd1.myworkdayjobs.com",
    "analogdevices.wd1.myworkdayjobs.com", "autodesk.wd1.myworkdayjobs.com", "barings.wd1.myworkdayjobs.com",
    "basecamp.wd1.myworkdayjobs.com", "bcbsaz.wd1.myworkdayjobs.com", "bdx.wd1.myworkdayjobs.com",
    "bjswholesaleclub.wd1.myworkdayjobs.com", "bloomberg.wd1.myworkdayjobs.com", "boseallaboutme.wd1.myworkdayjobs.com",
    "cambiumlearning.wd1.myworkdayjobs.com", "capitalone.wd1.myworkdayjobs.com", "cardinalhealth.wd1.myworkdayjobs.com",
    "centier.wd1.myworkdayjobs.com", "cni.wd1.myworkdayjobs.com", "collegeboard.wd1.myworkdayjobs.com",
    "cox.wd1.myworkdayjobs.com", "cvshealth.wd1.myworkdayjobs.com", "daiichisankyo.wd1.myworkdayjobs.com",
    "davidyurman.wd1.myworkdayjobs.com", "dechert.wd1.myworkdayjobs.com", "draftkings.wd1.myworkdayjobs.com",
    "dutchbros.wd1.myworkdayjobs.com", "endurance.wd1.myworkdayjobs.com", "finishline.wd1.myworkdayjobs.com",
    "fisker.wd1.myworkdayjobs.com", "forcepoint.wd1.myworkdayjobs.com", "fractal.wd1.myworkdayjobs.com",
    "gen.wd1.myworkdayjobs.com", "genpt.wd1.myworkdayjobs.com", "ghc.wd1.myworkdayjobs.com",
    "ghr.wd1.myworkdayjobs.com", "gnw.wd1.myworkdayjobs.com", "gogo.wd1.myworkdayjobs.com",
    "guidehouse.wd1.myworkdayjobs.com", "highmarkhealth.wd1.myworkdayjobs.com", "hitachi.wd1.myworkdayjobs.com",
    "ibotta.wd1.myworkdayjobs.com", "intel.wd1.myworkdayjobs.com", "issgovernance.wd1.myworkdayjobs.com",
    "justfab.wd1.myworkdayjobs.com", "kar.wd1.myworkdayjobs.com", "lambweston.wd1.myworkdayjobs.com",
    "lexmark.wd1.myworkdayjobs.com", "maritz.wd1.myworkdayjobs.com", "modernatx.wd1.myworkdayjobs.com",
    "ncr.wd1.myworkdayjobs.com", "ncratleos.wd1.myworkdayjobs.com", "neighborlybrands.wd1.myworkdayjobs.com",
    "ntrs.wd1.myworkdayjobs.com", "ntst.wd1.myworkdayjobs.com", "pae.wd1.myworkdayjobs.com",
    "pinnacle.wd1.myworkdayjobs.com", "priceline.wd1.myworkdayjobs.com", "redfcu.wd1.myworkdayjobs.com",
    "riteaid.wd1.myworkdayjobs.com", "rockwellautomation.wd1.myworkdayjobs.com", "rogersbh.wd1.myworkdayjobs.com",
    "sands.wd1.myworkdayjobs.com", "sedgwick.wd1.myworkdayjobs.com", "sentara.wd1.myworkdayjobs.com",
    "signetjewelers.wd1.myworkdayjobs.com", "sonos.wd1.myworkdayjobs.com", "sonyglobal.wd1.myworkdayjobs.com",
    "statestreet.wd1.myworkdayjobs.com", "tencent.wd1.myworkdayjobs.com", "tgs.wd1.myworkdayjobs.com",
    "travelhrportal.wd1.myworkdayjobs.com", "trimble.wd1.myworkdayjobs.com", "tsys.wd1.myworkdayjobs.com",
    "uline.wd1.myworkdayjobs.com", "univision.wd1.myworkdayjobs.com", "wellsky.wd1.myworkdayjobs.com",
    "xcelenergy.wd1.myworkdayjobs.com"
]

def add_workday_batch():
    added = 0
    skipped = 0
    print(f"Adding {len(WORKDAY_URLS)} Workday companies...")
    
    for url in WORKDAY_URLS:
        # Slug is everything before .myworkdayjobs.com
        full_slug = url.replace(".myworkdayjobs.com", "")
        # The primary name for fetching is the full slug (e.g., nvidia.wd5)
        success = database.add_company(
            name=full_slug,
            ats_url=f"https://{url}/en-US/Careers",
            ats_provider="workday"
        )
        if success:
            added += 1
        else:
            skipped += 1
            
    print(f"\nDone! Added: {added}, Skipped: {skipped}")

if __name__ == "__main__":
    add_workday_batch()
