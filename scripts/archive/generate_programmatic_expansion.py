import json
import os

def generate_programmatic_expansion():
    expansion = {
        "job_terminology": [
            {
                "category": "AWS Services (Auto-generated)",
                "items": [
                    { "name": f"AWS {svc}", "synonyms": [svc] } for svc in [
                        "Lambda", "S3", "EC2", "RDS", "DynamoDB", "ECS", "EKS", "Fargate", "Athena", "Redshift",
                        "Glue", "Kinesis", "Step Functions", "SQS", "SNS", "API Gateway", "CloudFront", "Route53",
                        "AppSync", "Amplify", "Cognito", "IAM", "VPC", "CloudWatch", "CloudTrail", "Config", "KMS",
                        "Secrets Manager", "SSM", "CodeCommit", "CodeBuild", "CodeDeploy", "CodePipeline", "X-Ray"
                    ]
                ]
            },
            {
                "category": "Azure Services (Auto-generated)",
                "items": [
                    { "name": f"Azure {svc}", "synonyms": [svc] } for svc in [
                        "Functions", "App Service", "Virtual Machines", "SQL Database", "Cosmos DB", "AKS", "Container Apps",
                        "Data Factory", "Synapse Analytics", "Logic Apps", "Service Bus", "Event Grid", "Front Door", "Application Gateway"
                    ]
                ]
            },
            {
                "category": "Python Ecosystem (Auto-generated)",
                "items": [
                    { "name": svc, "synonyms": [] } for svc in [
                        "NumPy", "Pandas", "Matplotlib", "SciPy", "Scikit-Learn", "TensorFlow", "PyTorch", "Keras", "NLTK", "Spacy",
                        "Flask", "Django", "FastAPI", "Celery", "SQLAlchemy", "Requests", "Selenium", "PyTest", "Aiohttp", "Pydantic"
                    ]
                ]
            },
            {
                "category": "Javascript Ecosystem (Auto-generated)",
                "items": [
                    { "name": svc, "synonyms": [] } for svc in [
                        "React", "Vue", "Angular", "Next.js", "Nuxt.js", "Svelte", "Redux", "MobX", "Zustand", "Express", "NestJS",
                        "Fastify", "Jest", "Cypress", "Playwright", "Webpack", "Vite", "Turbopack", "Axios", "Lodash"
                    ]
                ]
            }
        ]
    }
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_path = os.path.join(base_dir, "us_ats_jobs", "intelligence", "programmatic_expansion.json")
    
    with open(output_path, "w") as f:
        json.dump(expansion, f, indent=4)
        
    print(f"✅ Programmatic expansion generated at {output_path}")

if __name__ == "__main__":
    generate_programmatic_expansion()
