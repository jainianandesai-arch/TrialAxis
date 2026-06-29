# Last eTMF sync: 2026-06-27 11:12:41
"""
TMF Intelligence System — Trial Portfolio
Primary Key: TAX Study ID (assigned by TrialAxis CRO internal system)
External IDs (NCT, EudraCT, Protocol No) are reference fields only.
Statuses driven by eTMF Excel import — not hardcoded.
"""

TRIALS = {   'TAX-2026-001': {   'tax_id': 'TAX-2026-001',
                        'nct_id': 'NCT05499130',
                        'sponsor_ref': 'TV48574-UC-30068',
                        'ref_type': 'Study Code',
                        'eudract': '2024-511089-36-00',
                        'short_name': 'RELIEVE UCCD',
                        'drug': 'TEV-48574',
                        'sponsor': 'Teva Branded Pharmaceutical Products R&D, '
                                   'Inc.',
                        'phase': 'Phase 2b',
                        'condition': "Ulcerative Colitis + Crohn's Disease",
                        'condition_type': ['UC', 'CD'],
                        'design': 'Randomized, Double-Blind, '
                                  'Placebo-Controlled, Dose-Ranging',
                        'duration': '14 weeks',
                        'ind_number': '157634',
                        'protocol_date': '2022-02-03',
                        'latest_amendment': 'Amendment 04',
                        'latest_amendment_date': '2024-07-08',
                        'countries': ['USA', 'Japan', 'Spain', 'France'],
                        'patients_screened': 563,
                        'patients_randomized': 229,
                        'primary_objective': 'Determine pharmacokinetics, '
                                             'efficacy, safety, and '
                                             'tolerability of TEV-48574 in '
                                             'adults with moderate to severe '
                                             'UC or CD',
                        'primary_endpoint': 'Clinical response at Week 14 '
                                            'based on disease activity scores',
                        'inclusion_criteria': [   'Adults 18-75 years with '
                                                  'moderate to severe UC or CD',
                                                  'Confirmed diagnosis by '
                                                  'endoscopy and histology',
                                                  'Inadequate response or '
                                                  'intolerance to conventional '
                                                  'therapy',
                                                  'Mayo score ≥6 (UC) or CDAI '
                                                  '≥220 (CD)'],
                        'exclusion_criteria': [   'Current diagnosis of '
                                                  'fulminant colitis or toxic '
                                                  'megacolon',
                                                  'Prior exposure to TEV-48574',
                                                  'Active infection including '
                                                  'TB',
                                                  'Hemoglobin <9 g/dL'],
                        'amendment_history': [   {   'version': 'Original',
                                                     'date': '2022-02-03',
                                                     'patients_at_time': '0 '
                                                                         'randomized'},
                                                 {   'version': 'Amendment 01',
                                                     'date': '2022-06-13',
                                                     'patients_at_time': '0 '
                                                                         'randomized'},
                                                 {   'version': 'Amendment 01 '
                                                                '(JP01)',
                                                     'date': '2022-08-15',
                                                     'patients_at_time': '0 '
                                                                         'enrolled'},
                                                 {   'version': 'Amendment 02 '
                                                                '(JP02)',
                                                     'date': '2023-01-13',
                                                     'patients_at_time': '2 '
                                                                         'randomized'},
                                                 {   'version': 'Amendment 03 '
                                                                '(JP03/ES01)',
                                                     'date': '2023-06-28',
                                                     'patients_at_time': '9 '
                                                                         'randomized'},
                                                 {   'version': 'Amendment 04 '
                                                                '(JP05/ES01/FR01)',
                                                     'date': '2024-07-08',
                                                     'patients_at_time': '229 '
                                                                         'randomized'}],
                        'tmf_documents': {   'Protocol (Final)': {   'status': 'Complete',
                                                                     'date': '2024-07-08',
                                                                     'version': 'Amendment '
                                                                                '04'},
                                             'Investigator Agreement': {   'status': 'Missing',
                                                                           'date': None,
                                                                           'version': None},
                                             'Ethics Committee Approval': {   'status': 'Missing',
                                                                              'date': None,
                                                                              'version': None},
                                             'IND Approval': {   'status': 'Missing',
                                                                 'date': None,
                                                                 'version': None},
                                             'Informed Consent Form': {   'status': 'Missing',
                                                                          'date': None,
                                                                          'version': None},
                                             'Monitoring Plan': {   'status': 'Missing',
                                                                    'date': None,
                                                                    'version': None},
                                             'Delegation of Authority Log': {   'status': 'Missing',
                                                                                'date': None,
                                                                                'version': None},
                                             'Lab Certification (Central)': {   'status': 'Missing',
                                                                                'date': None,
                                                                                'version': None},
                                             'Site Initiation Visit Report': {   'status': 'Missing',
                                                                                 'date': None,
                                                                                 'version': None},
                                             'Monitoring Visit Reports': {   'status': 'Missing',
                                                                             'date': None,
                                                                             'version': None}},
                        'risk_level': 'High',
                        'notes': 'Multinational trial with country-specific '
                                 'amendments for Japan, Spain, France. High '
                                 'complexity due to dual indication (UC+CD).'},
    'TAX-2026-002': {   'tax_id': 'TAX-2026-002',
                        'nct_id': 'NCT04023396',
                        'sponsor_ref': 'ABX464-104',
                        'ref_type': 'Protocol No',
                        'eudract': '2019-000733-39',
                        'short_name': 'ABX464-104',
                        'drug': 'ABX464 (Obefazimod)',
                        'sponsor': 'ABIVAX',
                        'phase': 'Phase 2b',
                        'condition': 'Ulcerative Colitis',
                        'condition_type': ['UC'],
                        'design': 'Open-label, Efficacy and Safety, '
                                  'Maintenance Therapy',
                        'duration': '52-100 weeks (maintenance)',
                        'ind_number': '141396',
                        'protocol_date': '2022-07-11',
                        'latest_amendment': 'Version 5.1',
                        'latest_amendment_date': '2022-07-11',
                        'countries': [   'Belgium',
                                         'Netherlands',
                                         'France',
                                         'UK',
                                         'USA'],
                        'patients_screened': None,
                        'patients_randomized': None,
                        'primary_objective': 'Evaluate efficacy and safety of '
                                             'ABX464 as maintenance therapy in '
                                             'moderate to severe UC',
                        'primary_endpoint': 'Clinical remission at Week 48 per '
                                            'modified Mayo score',
                        'inclusion_criteria': [   'Adults with moderate to '
                                                  'severe UC',
                                                  'Completion of induction '
                                                  'study ABX464-103',
                                                  'Clinical response at Day '
                                                  '113 of induction study',
                                                  'Adequate contraception for '
                                                  'women of childbearing '
                                                  'potential'],
                        'exclusion_criteria': [   'Failure to complete '
                                                  'induction study ABX464-103',
                                                  'Serious adverse event '
                                                  'during induction',
                                                  'Active cardiac disease',
                                                  'Pregnancy or breastfeeding'],
                        'amendment_history': [   {   'version': 'Version 1.0',
                                                     'date': '2019-01-01',
                                                     'patients_at_time': 'Study '
                                                                         'initiation'},
                                                 {   'version': 'Version 5.1',
                                                     'date': '2022-07-11',
                                                     'patients_at_time': 'Ongoing'}],
                        'vendor_ecosystem': {   'CRO / Data Management': 'IQVIA '
                                                                         'RDS '
                                                                         'France, '
                                                                         'La '
                                                                         'Défense, '
                                                                         'France',
                                                'miRNA Analysis': 'Biogazelle, '
                                                                  'Gent, '
                                                                  'Belgium',
                                                'Histopathology (RHI)': 'Cerba '
                                                                        'Research, '
                                                                        'Montpellier, '
                                                                        'France',
                                                'Central Laboratory': 'Eurofins '
                                                                      'Central '
                                                                      'Laboratory, '
                                                                      'Breda, '
                                                                      'Netherlands',
                                                'Central Imaging Review': 'Clario '
                                                                          'Medical '
                                                                          'Imaging, '
                                                                          'London, '
                                                                          'UK',
                                                'Pharmacovigilance': 'Voisin '
                                                                     'Consulting '
                                                                     '(VCLS), '
                                                                     'Boulogne-Billancourt, '
                                                                     'France',
                                                'Coordinating Investigator': 'Prof. '
                                                                             'Severine '
                                                                             'Vermeire, '
                                                                             'University '
                                                                             'Hospitals '
                                                                             'Leuven, '
                                                                             'Belgium'},
                        'tmf_documents': {   'Protocol (Final)': {   'status': 'Complete',
                                                                     'date': '2022-07-11',
                                                                     'version': 'v5.1'},
                                             'Investigator Agreement': {   'status': 'Missing',
                                                                           'date': None,
                                                                           'version': None},
                                             'Ethics Committee Approval': {   'status': 'Missing',
                                                                              'date': None,
                                                                              'version': None},
                                             'IND Approval': {   'status': 'Missing',
                                                                 'date': None,
                                                                 'version': None},
                                             'Informed Consent Form': {   'status': 'Missing',
                                                                          'date': None,
                                                                          'version': None},
                                             'Vendor Contracts (CRO)': {   'status': 'Missing',
                                                                           'date': None,
                                                                           'version': None},
                                             'Central Lab Certification': {   'status': 'Missing',
                                                                              'date': None,
                                                                              'version': None},
                                             'Imaging Charter (Central)': {   'status': 'Missing',
                                                                              'date': None,
                                                                              'version': None},
                                             'Pharmacovigilance Agreement': {   'status': 'Missing',
                                                                                'date': None,
                                                                                'version': None},
                                             'Delegation of Authority Log': {   'status': 'Missing',
                                                                                'date': None,
                                                                                'version': None},
                                             'Monitoring Visit Reports': {   'status': 'Missing',
                                                                             'date': None,
                                                                             'version': None}},
                        'risk_level': 'Medium',
                        'notes': 'Complex multi-vendor ecosystem across 6 '
                                 'countries. Maintenance study — requires '
                                 'ongoing vendor certification tracking.'},
    'TAX-2026-003': {   'tax_id': 'TAX-2026-003',
                        'nct_id': 'NCT04130919',
                        'sponsor_ref': 'GS-US-365-4237',
                        'ref_type': 'Study Number',
                        'eudract': '2019-001430-33',
                        'short_name': 'GS-US-365-4237',
                        'drug': 'GS-4875 (Tilpisertib)',
                        'sponsor': 'Gilead Sciences, Inc.',
                        'phase': 'Phase 2',
                        'condition': 'Ulcerative Colitis',
                        'condition_type': ['UC'],
                        'design': 'Blinded, Randomized, Placebo-Controlled',
                        'duration': 'Not specified (induction)',
                        'ind_number': '143174',
                        'protocol_date': '2019-03-25',
                        'latest_amendment': 'Amendment 2',
                        'latest_amendment_date': '2020-06-19',
                        'countries': ['USA', 'EU', 'Switzerland', 'Russia'],
                        'patients_screened': None,
                        'patients_randomized': None,
                        'primary_objective': 'Evaluate efficacy and safety of '
                                             'GS-4875 in moderately to '
                                             'severely active UC',
                        'primary_endpoint': 'Clinical remission per adapted '
                                            'Mayo score at Week 8',
                        'inclusion_criteria': [   'Adults with moderately to '
                                                  'severely active UC',
                                                  'Confirmed diagnosis by '
                                                  'endoscopy',
                                                  'Inadequate response to '
                                                  'aminosalicylates, '
                                                  'corticosteroids, or '
                                                  'immunomodulators',
                                                  'Mayo score ≥6 with '
                                                  'endoscopic subscore ≥2'],
                        'exclusion_criteria': [   'Disease limited to rectum '
                                                  '(ulcerative proctitis)',
                                                  'Current diagnosis of '
                                                  "Crohn's disease or "
                                                  'indeterminate colitis',
                                                  'Azathioprine or 6-MP within '
                                                  '10 days of baseline',
                                                  'Hemoglobin <9 g/dL'],
                        'amendment_history': [   {   'version': 'Original',
                                                     'date': '2019-03-25',
                                                     'patients_at_time': '0'},
                                                 {   'version': 'Amendment 1',
                                                     'date': '2019-07-18',
                                                     'patients_at_time': 'Enrollment '
                                                                         'ongoing'},
                                                 {   'version': 'Amendment 1.1 '
                                                                '(CH/RU/VHP)',
                                                     'date': '2019-12-11',
                                                     'patients_at_time': 'Country-specific'},
                                                 {   'version': 'Amendment 2',
                                                     'date': '2020-06-19',
                                                     'patients_at_time': 'Ongoing'}],
                        'tmf_documents': {   'Protocol (Final)': {   'status': 'Complete',
                                                                     'date': '2020-06-19',
                                                                     'version': 'Amendment '
                                                                                '2'},
                                             'Investigator Agreement': {   'status': 'Missing',
                                                                           'date': None,
                                                                           'version': None},
                                             'Ethics Committee Approval': {   'status': 'Missing',
                                                                              'date': None,
                                                                              'version': None},
                                             'IND Approval': {   'status': 'Missing',
                                                                 'date': None,
                                                                 'version': None},
                                             'Informed Consent Form': {   'status': 'Missing',
                                                                          'date': None,
                                                                          'version': None},
                                             'Monitoring Plan': {   'status': 'Missing',
                                                                    'date': None,
                                                                    'version': None},
                                             'Delegation of Authority Log': {   'status': 'Missing',
                                                                                'date': None,
                                                                                'version': None},
                                             'Lab Certification': {   'status': 'Missing',
                                                                      'date': None,
                                                                      'version': None},
                                             'Site Initiation Visit Reports': {   'status': 'Missing',
                                                                                  'date': None,
                                                                                  'version': None},
                                             'Monitoring Visit Reports': {   'status': 'Missing',
                                                                             'date': None,
                                                                             'version': None}},
                        'risk_level': 'High',
                        'notes': 'Ethics Committee approval flagged as '
                                 'expired. Non-IND sites in '
                                 'EU/Switzerland/Russia require separate '
                                 'regulatory tracking.'},
    'TAX-2026-004': {   'tax_id': 'TAX-2026-004',
                        'nct_id': 'NCT05068284',
                        'sponsor_ref': 'M20-371',
                        'ref_type': 'Study Number',
                        'eudract': '2021-002869-18',
                        'short_name': 'AIM-CD (M20-371)',
                        'drug': 'ABBV-154',
                        'sponsor': 'AbbVie Deutschland GmbH & Co. KG',
                        'phase': 'Phase 2',
                        'condition': "Crohn's Disease",
                        'condition_type': ['CD'],
                        'design': 'Randomized, Double-Blind, '
                                  'Placebo-Controlled',
                        'duration': 'Not specified',
                        'ind_number': 'On file at AbbVie',
                        'protocol_date': '2020-12-01',
                        'latest_amendment': 'Version 4.0',
                        'latest_amendment_date': '2022-12-20',
                        'countries': ['USA', 'EU', 'Germany', 'Belgium'],
                        'patients_screened': 200,
                        'patients_randomized': None,
                        'primary_objective': 'Evaluate safety and efficacy of '
                                             'ABBV-154 in moderately to '
                                             "severely active Crohn's Disease",
                        'primary_endpoint': 'Clinical remission per CDAI at '
                                            'Week 12',
                        'inclusion_criteria': [   'Adults 18-75 with '
                                                  'moderately to severely '
                                                  'active CD',
                                                  'CDAI score 220-450 at '
                                                  'screening',
                                                  'Confirmed CD diagnosis ≥3 '
                                                  'months prior',
                                                  'Inadequate response to '
                                                  'biologics or '
                                                  'immunomodulators'],
                        'exclusion_criteria': [   'Current short bowel '
                                                  'syndrome',
                                                  'Active fistulizing disease '
                                                  'requiring surgery',
                                                  'Prior exposure to anti-TNF '
                                                  '>2 agents',
                                                  'Active or latent TB'],
                        'amendment_history': [   {   'version': 'Version 1.0',
                                                     'date': '2020-12-01',
                                                     'patients_at_time': '0'},
                                                 {   'version': 'Version 1.1 '
                                                                '(Germany '
                                                                'only)',
                                                     'date': '2021-03-01',
                                                     'patients_at_time': '0'},
                                                 {   'version': 'Version 2.0',
                                                     'date': '2021-08-01',
                                                     'patients_at_time': 'Enrollment '
                                                                         'started'},
                                                 {   'version': 'Version 2.1 '
                                                                '(Belgium '
                                                                'only)',
                                                     'date': '2021-10-01',
                                                     'patients_at_time': 'Ongoing'},
                                                 {   'version': 'Version 2.2 '
                                                                '(Germany '
                                                                'only)',
                                                     'date': '2021-12-01',
                                                     'patients_at_time': 'Ongoing'},
                                                 {   'version': 'Version 3.0',
                                                     'date': '2022-05-01',
                                                     'patients_at_time': 'Ongoing'},
                                                 {   'version': 'Version 4.0',
                                                     'date': '2022-12-20',
                                                     'patients_at_time': '200 '
                                                                         'planned '
                                                                         'sites'}],
                        'tmf_documents': {   'Protocol (Final)': {   'status': 'Complete',
                                                                     'date': '2022-12-20',
                                                                     'version': 'v4.0'},
                                             'Investigator Agreement': {   'status': 'Missing',
                                                                           'date': None,
                                                                           'version': None},
                                             'Ethics Committee Approval': {   'status': 'Missing',
                                                                              'date': None,
                                                                              'version': None},
                                             'IND Approval': {   'status': 'Missing',
                                                                 'date': None,
                                                                 'version': None},
                                             'Informed Consent Form': {   'status': 'Missing',
                                                                          'date': None,
                                                                          'version': None},
                                             'Delegation of Authority Log': {   'status': 'Missing',
                                                                                'date': None,
                                                                                'version': None},
                                             'Lab Certification': {   'status': 'Missing',
                                                                      'date': None,
                                                                      'version': None},
                                             'Site Initiation Visit Reports': {   'status': 'Missing',
                                                                                  'date': None,
                                                                                  'version': None},
                                             'Monitoring Visit Reports': {   'status': 'Missing',
                                                                             'date': None,
                                                                             'version': None},
                                             'Country-Specific Amendments (DE/BE)': {   'status': 'Missing',
                                                                                        'date': None,
                                                                                        'version': None}},
                        'risk_level': 'High',
                        'notes': 'Large 200-site trial. Country-specific '
                                 'amendments for Germany and Belgium add '
                                 'complexity. 12 investigator agreements '
                                 'outstanding.'},
    'TAX-2026-005': {   'tax_id': 'TAX-2026-005',
                        'nct_id': 'NCT05013905',
                        'sponsor_ref': 'PR200-103',
                        'ref_type': 'Protocol No',
                        'eudract': '2021-000092-37',
                        'short_name': 'APOLLO-CD (PR200-103)',
                        'drug': 'PRA023 (Tulisokibart / MK-7240)',
                        'sponsor': 'Prometheus Biosciences, Inc. (acquired by '
                                   'Merck)',
                        'phase': 'Phase 2a',
                        'condition': "Crohn's Disease",
                        'condition_type': ['CD'],
                        'design': 'Multi-Center, Open-Label',
                        'duration': 'Not specified',
                        'ind_number': 'On file',
                        'protocol_date': '2022-06-28',
                        'latest_amendment': 'Version 4.0',
                        'latest_amendment_date': '2022-06-28',
                        'countries': ['USA', 'EU'],
                        'patients_screened': None,
                        'patients_randomized': None,
                        'primary_objective': 'Evaluate safety, efficacy, and '
                                             'pharmacokinetics of PRA023 in '
                                             'moderately to severely active CD',
                        'primary_endpoint': 'Clinical response and remission '
                                            'per CDAI at Week 12; PK profile '
                                            'characterization',
                        'inclusion_criteria': [   'Adults with moderately to '
                                                  'severely active CD',
                                                  'CDAI ≥220 at screening',
                                                  'Elevated CRP or fecal '
                                                  'calprotectin',
                                                  'Inadequate response or '
                                                  'intolerance to ≥1 biologic'],
                        'exclusion_criteria': [   'Current ostomy or ileoanal '
                                                  'pouch',
                                                  'Active infection',
                                                  'Prior treatment with '
                                                  'anti-TL1A therapy',
                                                  'Malignancy within 5 years'],
                        'amendment_history': [   {   'version': 'Version 1.0',
                                                     'date': '2021-08-01',
                                                     'patients_at_time': '0'},
                                                 {   'version': 'Version 2.0',
                                                     'date': '2021-12-01',
                                                     'patients_at_time': 'Enrollment '
                                                                         'started'},
                                                 {   'version': 'Version 3.0',
                                                     'date': '2022-03-01',
                                                     'patients_at_time': 'Ongoing'},
                                                 {   'version': 'Version 4.0',
                                                     'date': '2022-06-28',
                                                     'patients_at_time': 'Ongoing'}],
                        'tmf_documents': {   'Protocol (Final)': {   'status': 'Complete',
                                                                     'date': '2022-06-28',
                                                                     'version': 'v4.0'},
                                             'Investigator Agreement': {   'status': 'Missing',
                                                                           'date': None,
                                                                           'version': None},
                                             'Ethics Committee Approval': {   'status': 'Missing',
                                                                              'date': None,
                                                                              'version': None},
                                             'IND Approval': {   'status': 'Missing',
                                                                 'date': None,
                                                                 'version': None},
                                             'Informed Consent Form': {   'status': 'Missing',
                                                                          'date': None,
                                                                          'version': None},
                                             'PK Analysis Plan': {   'status': 'Missing',
                                                                     'date': None,
                                                                     'version': None},
                                             'Delegation of Authority Log': {   'status': 'Missing',
                                                                                'date': None,
                                                                                'version': None},
                                             'Lab Certification': {   'status': 'Missing',
                                                                      'date': None,
                                                                      'version': None},
                                             'Sponsor Change Documentation': {   'status': 'Missing',
                                                                                 'date': None,
                                                                                 'version': None},
                                             'Monitoring Visit Reports': {   'status': 'Missing',
                                                                             'date': None,
                                                                             'version': None}},
                        'risk_level': 'Medium',
                        'notes': 'Sponsor acquired by Merck — transfer '
                                 'documentation outstanding. Two sites still '
                                 'using outdated consent form version.'},
    'TAX-2026-006': {   'tax_id': 'TAX-2026-006',
                        'nct_id': 'NCT04804540',
                        'sponsor_ref': 'MLN0002-4020',
                        'ref_type': 'Study Number',
                        'eudract': 'N/A',
                        'short_name': 'Vedolizumab-4020',
                        'drug': 'Vedolizumab (Entyvio)',
                        'sponsor': 'Takeda Biopharmaceuticals India Pvt. Ltd.',
                        'phase': 'Phase 4',
                        'condition': "Ulcerative Colitis and Crohn's Disease",
                        'condition_type': [],
                        'design': 'See protocol',
                        'duration': 'See protocol',
                        'ind_number': 'On file',
                        'protocol_date': '2026-06-26',
                        'latest_amendment': 'Version 1.0',
                        'latest_amendment_date': '2026-06-26',
                        'countries': ['India'],
                        'patients_screened': None,
                        'patients_randomized': None,
                        'primary_objective': 'To evaluate the safety and '
                                             'efficacy of vedolizumab in '
                                             'Indian patients with Ulcerative '
                                             "Colitis and Crohn's Disease.",
                        'primary_endpoint': 'Safety and efficacy of '
                                            'vedolizumab in Indian patients '
                                            'with Ulcerative Colitis and '
                                            "Crohn's Disease as assessed by "
                                            'study-defined measures.',
                        'inclusion_criteria': ['See protocol'],
                        'exclusion_criteria': ['See protocol'],
                        'amendment_history': [   {   'version': 'Version 1.0',
                                                     'date': '2026-06-26',
                                                     'patients_at_time': '0'}],
                        'tmf_documents': {   'Protocol (Final)': {   'status': 'Complete',
                                                                     'date': '2026-06-26',
                                                                     'version': 'v1.0'},
                                             'Investigator Agreement': {   'status': 'Missing',
                                                                           'date': None,
                                                                           'version': None},
                                             'Ethics Committee Approval': {   'status': 'Missing',
                                                                              'date': None,
                                                                              'version': None},
                                             'IND Approval': {   'status': 'Missing',
                                                                 'date': None,
                                                                 'version': None},
                                             'Informed Consent Form': {   'status': 'Missing',
                                                                          'date': None,
                                                                          'version': None},
                                             'Monitoring Plan': {   'status': 'Missing',
                                                                    'date': None,
                                                                    'version': None}},
                        'risk_level': 'Medium',
                        'notes': 'Auto-ingested via TMF Intelligence System.'},
    'TAX-2026-007': {   'tax_id': 'TAX-2026-007',
                        'nct_id': 'NCT03341962',
                        'sponsor_ref': 'P2-IMU-838-UC',
                        'ref_type': 'Protocol No',
                        'eudract': 'N/A',
                        'short_name': 'CALDOSE-1',
                        'drug': 'IMU-838 (vidofludimus calcium)',
                        'sponsor': 'Immunic AG',
                        'phase': 'Phase 2',
                        'condition': 'Moderate-to-severe ulcerative colitis',
                        'condition_type': [],
                        'design': 'See protocol',
                        'duration': 'See protocol',
                        'ind_number': 'On file',
                        'protocol_date': '2026-06-26',
                        'latest_amendment': 'Version 1.0',
                        'latest_amendment_date': '2026-06-26',
                        'countries': [   'Germany',
                                         'Netherlands',
                                         'United Kingdom',
                                         'Poland'],
                        'patients_screened': None,
                        'patients_randomized': None,
                        'primary_objective': 'To evaluate the efficacy and '
                                             'safety of IMU-838 for induction '
                                             'and maintenance therapy in '
                                             'patients with moderate-to-severe '
                                             'ulcerative colitis.',
                        'primary_endpoint': 'Proportion of patients with both '
                                            'symptomatic remission and '
                                            'endoscopic healing at Week 10, '
                                            'comparing pooled 30 mg/day and 45 '
                                            'mg/day IMU-838 groups versus '
                                            'placebo.',
                        'inclusion_criteria': ['See protocol'],
                        'exclusion_criteria': ['See protocol'],
                        'amendment_history': [   {   'version': 'Version 1.0',
                                                     'date': '2026-06-26',
                                                     'patients_at_time': '0'}],
                        'tmf_documents': {   'Protocol (Final)': {   'status': 'Complete',
                                                                     'date': '2026-06-26',
                                                                     'version': 'v1.0'},
                                             'Investigator Agreement': {   'status': 'Missing',
                                                                           'date': None,
                                                                           'version': None},
                                             'Ethics Committee Approval': {   'status': 'Missing',
                                                                              'date': None,
                                                                              'version': None},
                                             'IND Approval': {   'status': 'Missing',
                                                                 'date': None,
                                                                 'version': None},
                                             'Informed Consent Form': {   'status': 'Missing',
                                                                          'date': None,
                                                                          'version': None},
                                             'Monitoring Plan': {   'status': 'Missing',
                                                                    'date': None,
                                                                    'version': None}},                        'risk_level': 'Medium',                        'notes': 'Auto-ingested via TMF Intelligence System.'},
    "TAX-2026-008": {
        "tax_id": "TAX-2026-008",
        "nct_id": "N/A",
        "eudract": "2020-003507-34",
        "protocol_no": "APD334-210",
        "study_number": "APD334-210",
        "short_name": "GLADIATOR UC",
        "drug": "Etrasimod (APD334)",
        "sponsor": "Arena Pharmaceuticals, Inc.",
        "phase": "Phase 2",
        "condition": "Ulcerative Colitis",
        "condition_type": [],
        "design": "See protocol",
        "duration": "See protocol",
        "ind_number": "125154",
        "protocol_date": "2020-07-20",
        "latest_amendment": "Amendment 2.0",
        "latest_amendment_date": "2022-08-04",
        "countries": ["United States", "Canada", "Europe", "Asia Pacific", "Middle East", "Africa"],
        "patients_screened": None,
        "patients_randomized": None,
        "primary_objective": "To assess the efficacy of etrasimod on clinical remission in subjects with moderately active ulcerative colitis (UC) after 52 weeks of treatment.",
        "primary_endpoint": "Clinical remission in subjects with moderately active ulcerative colitis after 52 weeks of treatment with etrasimod.",
        "pdf_filename": "TAX-2026-008_GLADIATOR-UC_APD334-210_Amendment_Amendment-2.0_2022-08-04.pdf",
        "inclusion_criteria": ["See protocol"],
        "exclusion_criteria": ["See protocol"],
        "amendment_history": [{"version": "Amendment 2.0", "date": "2022-08-04", "patients_at_time": "0"}],
        "tmf_documents": {
            "Protocol (Final)": {"status": "Complete", "date": "2022-08-04", "version": "Amendment 2.0"},
            "Investigator Agreement": {"status": "Missing", "date": None, "version": None},
            "Ethics Committee Approval": {"status": "Missing", "date": None, "version": None},
            "IND Approval": {"status": "Missing", "date": None, "version": None},
            "Informed Consent Form": {"status": "Missing", "date": None, "version": None},
            "Monitoring Plan": {"status": "Missing", "date": None, "version": None},
        },
        "risk_level": "Medium",
        "notes": "Auto-ingested via TMF Intelligence System.",
    },
}

TMF_ZONES = {
    "Zone 1": "Trial Management",
    "Zone 2": "Subject Information and Consent",
    "Zone 3": "Subject Identification",
    "Zone 4": "Site and Staff Information",
    "Zone 5": "Scientific and Medical Information",
    "Zone 6": "Investigational Medicinal Products",
    "Zone 7": "Regulatory and Ethics",
    "Zone 8": "Investigator Site File",
}

FLAG_RULES = {
    "Missing": {
        "action": "Locate or obtain document and file in TMF within 30 days.",
        "severity": "Critical",
    },
    "Expired": {
        "action": "Renew document and update TMF with current version immediately.",
        "severity": "Critical",
    },
    "Needs Review": {
        "action": "Review document for completeness and accuracy within 14 days.",
        "severity": "Warning",
    },
    "Pending": {
        "action": "Follow up with responsible party to obtain document.",
        "severity": "Warning",
    },
    "Complete": {
        "action": "No action required.",
        "severity": "OK",
    },}
