#!/bin/bash
# scripts/setup-mtls.sh
# Generate certificates for mTLS

set -e

CERT_DIR="./certs"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🔐 Setting up mTLS certificates for GraphMemory-IDE"
echo "Certificate directory: $PROJECT_ROOT/$CERT_DIR"

# Create certificate directory
mkdir -p "$PROJECT_ROOT/$CERT_DIR"
cd "$PROJECT_ROOT/$CERT_DIR"

# Generate CA private key
echo "📋 Generating Certificate Authority (CA) private key..."
openssl genrsa -out ca-key.pem 4096

# Generate CA certificate
echo "📋 Generating Certificate Authority (CA) certificate..."
openssl req -new -x509 -days 365 -key ca-key.pem -sha256 -out ca-cert.pem -subj \
    "/C=US/ST=CA/L=San Francisco/O=GraphMemory-IDE/OU=Security/CN=GraphMemory-CA"

# Generate server private key
echo "🖥️  Generating server private key..."
openssl genrsa -out server-key.pem 4096

# Generate server certificate signing request
echo "🖥️  Generating server certificate signing request..."
openssl req -subj "/C=US/ST=CA/L=San Francisco/O=GraphMemory-IDE/OU=MCP-Server/CN=mcp-server" \
    -sha256 -new -key server-key.pem -out server.csr

# Create extensions file for server certificate
echo "🖥️  Creating server certificate extensions..."
cat > server-extfile.cnf <<EOF
subjectAltName = DNS:mcp-server,DNS:localhost,IP:127.0.0.1,IP:0.0.0.0
extendedKeyUsage = serverAuth
EOF

# Generate server certificate
echo "🖥️  Generating server certificate..."
openssl x509 -req -days 365 -sha256 -in server.csr -CA ca-cert.pem -CAkey ca-key.pem \
    -out server-cert.pem -extfile server-extfile.cnf -CAcreateserial

# Generate client private key
echo "👤 Generating client private key..."
openssl genrsa -out client-key.pem 4096

# Generate client certificate signing request
echo "👤 Generating client certificate signing request..."
openssl req -subj "/C=US/ST=CA/L=San Francisco/O=GraphMemory-IDE/OU=MCP-Client/CN=mcp-client" \
    -new -key client-key.pem -out client.csr

# Create extensions file for client certificate
echo "👤 Creating client certificate extensions..."
cat > client-extfile.cnf <<EOF
extendedKeyUsage = clientAuth
EOF

# Generate client certificate
echo "👤 Generating client certificate..."
openssl x509 -req -days 365 -sha256 -in client.csr -CA ca-cert.pem -CAkey ca-key.pem \
    -out client-cert.pem -extfile client-extfile.cnf -CAcreateserial

# Set appropriate permissions
echo "🔒 Setting secure file permissions..."
chmod 400 ca-key.pem server-key.pem client-key.pem
chmod 444 ca-cert.pem server-cert.pem client-cert.pem

# Clean up temporary files
echo "🧹 Cleaning up temporary files..."
rm server.csr client.csr server-extfile.cnf client-extfile.cnf

# Verify certificates
echo "✅ Verifying certificate chain..."
openssl verify -CAfile ca-cert.pem server-cert.pem
openssl verify -CAfile ca-cert.pem client-cert.pem

# Display certificate information
echo ""
echo "📊 Certificate Information:"
echo "=========================="
echo "CA Certificate:"
openssl x509 -in ca-cert.pem -text -noout | grep -E "(Subject:|Not Before|Not After)"
echo ""
echo "Server Certificate:"
openssl x509 -in server-cert.pem -text -noout | grep -E "(Subject:|Not Before|Not After|DNS:|IP Address:)"
echo ""
echo "Client Certificate:"
openssl x509 -in client-cert.pem -text -noout | grep -E "(Subject:|Not Before|Not After)"

echo ""
echo "✅ mTLS certificates generated successfully in $PROJECT_ROOT/$CERT_DIR"
echo ""
echo "📝 Next steps:"
echo "   1. Set MTLS_ENABLED=true in your environment"
echo "   2. Restart the Docker containers"
echo "   3. Test mTLS connection on port 50051"
echo ""
echo "🔧 Test mTLS connection:"
echo "   openssl s_client -connect localhost:50051 -cert client-cert.pem -key client-key.pem -CAfile ca-cert.pem" 