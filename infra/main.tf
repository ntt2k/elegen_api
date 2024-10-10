# main.tf

provider "aws" {
  region = "us-east-1"
}

# VPC
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name = "tracking-system-vpc"
  }
}

# Subnet
resource "aws_subnet" "main" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.1.0/24"
  availability_zone = "us-east-1a"
  map_public_ip_on_launch = true

  tags = {
    Name = "tracking-system-subnet"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "tracking-system-igw"
  }
}

# Route Table
resource "aws_route_table" "main" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "tracking-system-rt"
  }
}

# Route Table Association
resource "aws_route_table_association" "main" {
  subnet_id      = aws_subnet.main.id
  route_table_id = aws_route_table.main.id
}

# Security Group for RDS
resource "aws_security_group" "rds" {
  name        = "tracking-system-rds-sg"
  description = "Security group for RDS"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }
}

# RDS Instance
resource "aws_db_instance" "tracking_db" {
  identifier           = "tracking-system-db"
  engine               = "postgres"
  engine_version       = "15.3"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  storage_type         = "gp2"
  username             = "postgres"
  password             = "postgres"  # In production, use AWS Secrets Manager
  db_name              = "tracking_db"
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name = aws_db_subnet_group.main.name
  skip_final_snapshot  = true
}

resource "aws_db_subnet_group" "main" {
  name       = "tracking-system-db-subnet-group"
  subnet_ids = [aws_subnet.main.id]

  tags = {
    Name = "Tracking System DB subnet group"
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "tracking-system-cluster"
}

# ECS Task Definition
resource "aws_ecs_task_definition" "tracking_system" {
  family                   = "tracking-system"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"

  container_definitions = jsonencode([
    {
      name  = "tracking-system"
      image = "tracking-system:latest"  # You need to push your image to ECR and use the URL here
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
        }
      ]
      environment = [
        {
          name  = "DATABASE_URL"
          value = "postgresql+asyncpg://postgres:postgres@${aws_db_instance.tracking_db.endpoint}/tracking_db"
        }
      ]
    }
  ])
}

# ECS Service
resource "aws_ecs_service" "tracking_system" {
  name            = "tracking-system-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.tracking_system.arn
  launch_type     = "FARGATE"
  desired_count   = 1

  network_configuration {
    subnets          = [aws_subnet.main.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.tracking_system.arn
    container_name   = "tracking-system"
    container_port   = 8000
  }
}

# Application Load Balancer
resource "aws_lb" "tracking_system" {
  name               = "tracking-system-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = [aws_subnet.main.id]
}

# ALB Target Group
resource "aws_lb_target_group" "tracking_system" {
  name        = "tracking-system-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"
}

# ALB Listener
resource "aws_lb_listener" "tracking_system" {
  load_balancer_arn = aws_lb.tracking_system.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.tracking_system.arn
  }
}

# Security Group for ALB
resource "aws_security_group" "alb" {
  name        = "tracking-system-alb-sg"
  description = "Security group for ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# API Gateway
resource "aws_api_gateway_rest_api" "tracking_system" {
  name        = "tracking-system-api"
  description = "Tracking System API"
}

resource "aws_api_gateway_resource" "proxy" {
  rest_api_id = aws_api_gateway_rest_api.tracking_system.id
  parent_id   = aws_api_gateway_rest_api.tracking_system.root_resource_id
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_method" "proxy" {
  rest_api_id   = aws_api_gateway_rest_api.tracking_system.id
  resource_id   = aws_api_gateway_resource.proxy.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "proxy" {
  rest_api_id = aws_api_gateway_rest_api.tracking_system.id
  resource_id = aws_api_gateway_resource.proxy.id
  http_method = aws_api_gateway_method.proxy.http_method

  integration_http_method = "ANY"
  type                    = "HTTP_PROXY"
  uri                     = "http://${aws_lb.tracking_system.dns_name}/{proxy}"
}

resource "aws_api_gateway_deployment" "tracking_system" {
  depends_on = [aws_api_gateway_integration.proxy]

  rest_api_id = aws_api_gateway_rest_api.tracking_system.id
  stage_name  = "prod"
}

# Outputs
output "api_gateway_url" {
  value = aws_api_gateway_deployment.tracking_system.invoke_url
}

output "load_balancer_dns" {
  value = aws_lb.tracking_system.dns_name
}

output "rds_endpoint" {
  value = aws_db_instance.tracking_db.endpoint
}