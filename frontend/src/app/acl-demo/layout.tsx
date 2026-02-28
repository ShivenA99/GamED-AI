import './acl-demo-override.css';

export default function ACLDemoLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <div className="acl-demo-root">{children}</div>;
}
