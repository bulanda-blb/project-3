
document.addEventListener('DOMContentLoaded',function(){
  const gm=id=>document.getElementById(id),
        btn=gm('submit-btn'),
        showErr=(id,m)=>{let e=gm('error-'+id); if(e)e.textContent=m},
        hideErr=id=>{let e=gm('error-'+id); if(e)e.textContent=''};

  // Department mapping
  const departments = {
  information_technology: [['software_development','Software Development'],['devops','DevOps'],['it_support','IT Support'],['network_engineering','Network Engineering'],['data_science','Data Science']],
  management: [['project_management','Project Management'],['operations','Operations'],['product_management','Product Management'],['strategy','Strategy'],['risk_management','Risk Management']],
  business: [['business_analysis','Business Analysis'],['sales','Sales'],['business_development','Business Development'],['customer_success','Customer Success']],
  finance: [['accounting','Accounting'],['audit','Audit'],['treasury','Treasury'],['investment_banking','Investment Banking'],['financial_planning','Financial Planning']],
  healthcare: [['nursing','Nursing'],['medical_administration','Medical Administration'],['healthcare_it','Healthcare IT'],['pharmacy','Pharmacy'],['physiotherapy','Physiotherapy']],
  education: [['teaching','Teaching'],['curriculum_development','Curriculum Development'],['admissions','Admissions'],['administration','Administration']],
  manufacturing: [['production','Production'],['quality_assurance','Quality Assurance'],['maintenance','Maintenance'],['supply_chain_management','Supply Chain Management']],
  construction: [['site_management','Site Management'],['civil_engineering','Civil Engineering'],['architecture','Architecture'],['safety','Safety']],
  retail: [['store_management','Store Management'],['merchandising','Merchandising'],['inventory_management','Inventory Management'],['customer_service','Customer Service']],
  hospitality: [['hotel_management','Hotel Management'],['food_beverage','Food & Beverage'],['front_desk','Front Desk'],['housekeeping','Housekeeping']],
  telecommunication: [['network_operations','Network Operations'],['technical_support','Technical Support'],['sales','Sales'],['engineering','Engineering']],
  transportation: [['logistics','Logistics'],['fleet_management','Fleet Management'],['transportation_planning','Transportation Planning'],['operations','Operations']],
  legal: [['corporate_law','Corporate Law'],['compliance','Compliance'],['contracts','Contracts'],['litigation','Litigation']],
  human_resources: [['recruitment','Recruitment'],['learning_development','Learning & Development'],['compensation_benefits','Compensation & Benefits'],['employee_relations','Employee Relations']],
  marketing_advertising: [['digital_marketing','Digital Marketing'],['brand_management','Brand Management'],['market_research','Market Research'],['public_relations','Public Relations']],
  media_entertainment: [['journalism','Journalism'],['editing','Editing'],['production','Production'],['social_media','Social Media']],
  research_development: [['lab_research','Lab Research'],['clinical_trials','Clinical Trials'],['product_innovation','Product Innovation']],
  non_profit: [['program_management','Program Management'],['fundraising','Fundraising'],['volunteer_coordination','Volunteer Coordination'],['advocacy','Advocacy']],
  government: [['policy_development','Policy Development'],['public_administration','Public Administration'],['regulatory_affairs','Regulatory Affairs']],
  agriculture: [['crop_science','Crop Science'],['farm_management','Farm Management'],['agricultural_technology','Agricultural Technology'],['quality_control','Quality Control']],
  energy_utilities: [['oil_gas','Oil & Gas'],['renewable_energy','Renewable Energy'],['safety_management','Safety Management'],['procurement','Procurement']],
  pharmaceutical: [['r_and_d','Research & Development'],['regulatory_affairs','Regulatory Affairs'],['quality_control','Quality Control'],['sales','Sales']],
  aerospace: [['avionics','Avionics'],['aircraft_design','Aircraft Design'],['maintenance','Maintenance'],['flight_operations','Flight Operations']],
  automotive: [['automotive_engineering','Automotive Engineering'],['manufacturing','Manufacturing'],['quality_assurance','Quality Assurance'],['sales','Sales']],
  tourism: [['travel_concierge','Travel Concierge'],['tour_operations','Tour Operations'],['event_planning','Event Planning'],['marketing','Marketing']],
  food_beverage: [['culinary_arts','Culinary Arts'],['quality_control','Quality Control'],['procurement','Procurement'],['sales','Sales']],
  beauty_wellness: [['cosmetology','Cosmetology'],['retail','Retail'],['product_development','Product Development'],['marketing','Marketing']],
  sports_recreation: [['coaching','Coaching'],['operations','Operations'],['sales','Sales'],['event_management','Event Management']],
  arts_culture: [['gallery_management','Gallery Management'],['curation','Curation'],['production','Production'],['education','Education']],
  environmental: [['environmental_consulting','Environmental Consulting'],['field_research','Field Research'],['policy_development','Policy Development']],
  security: [['physical_security','Physical Security'],['cybersecurity','Cybersecurity'],['investigations','Investigations']],
  consulting: [['strategy_consulting','Strategy Consulting'],['it_consulting','IT Consulting'],['management_consulting','Management Consulting'],['hr_consulting','HR Consulting']]
};

gm('industry').addEventListener('change', () => {
  const key = gm('industry').value;
  const opts = departments[key] || [];
  const sel = gm('department');
  sel.innerHTML = '<option value="">– Select Department –</option>';
  opts.forEach(([val,label]) => sel.appendChild(new Option(label,val)));
});


function toggleExperience() {
  const v = gm('experience_level').value;
  if (v === 'junior' || v === 'mid' || v === 'senior') {
    gm('group-experience_min').style.display = 'block';
    gm('group-experience_max').style.display = 'block';
  } else {
    // covers both “intern” and the initial empty value
    gm('group-experience_min').style.display = 'none';
    gm('group-experience_max').style.display = 'none';
  }
}
// hook only on change
gm('experience_level').addEventListener('change', () => {
  toggleExperience();
  validateField(gm('experience_level'));
  checkAll();
});
// call once to set initial hidden
toggleExperience();


// And replace your existing salaryLogic() with:

function toggleSalary() {
  const v = gm('salary_type').value;
  if (v === 'fixed') {
    gm('group-salary_min').style.display = 'none';
    gm('group-salary_max').style.display = 'block';
    gm('salary_min').value = 0;
  } else if (v === 'negotiable') {
    gm('group-salary_min').style.display = 'block';
    gm('group-salary_max').style.display = 'block';
  } else {
    // initial empty or invalid
    gm('group-salary_min').style.display = 'none';
    gm('group-salary_max').style.display = 'none';
  }
}
gm('salary_type').addEventListener('change', () => {
  toggleSalary();
  validateField(gm('salary_type'));
  checkAll();
});
toggleSalary();



  // Validation
  const required=[
    'contact_email','application_deadline','title','industry','department',
    'work_type','gender_requirement','experience_level','salary_type',
    'salary_min','salary_max','num_candidates_required','requirements',
    'preferred_skills','languages','benefits','location_type',
    'full_location_address','description', 'salary_frequency',
  ];

  function validateField(el){
    if(!el) return true;
    const id=el.id, v=el.value.trim(), t=el.type;
    let err='';
    if(el.required && !v) err='Required.';
    else if(t==='email'&&!/^\S+@\S+\.\S+$/.test(v)) err='Invalid email.';
    else if((t==='number'||/(min|max|required)$/.test(el.name))&&v&&isNaN(v)) err='Invalid number.';
    else if(['requirements','preferred_skills','benefits','languages'].includes(id)&&v&&!v.includes(',')) err='Use commas.';
    else if(id === 'description' && v.split(/\s+/).length < 50) {
      err = 'Description must be at least 50 words.';
     }
    if(err){showErr(id,err);return false;} hideErr(id); return true;
  }

  function checkAll(){
    btn.disabled = !required.every(id=>validateField(gm(id)));
  }

  required.forEach(id=>{
    const el=gm(id);
    if(!el) return;
    el.addEventListener('input', ()=>{validateField(el);checkAll();});
    el.addEventListener('blur',  ()=>{validateField(el);checkAll();});
  });

  // Initial check
  checkAll();
});
